"""The decision grader must reject wrong routing, missing evidence and unsafe plans."""
import copy
import importlib.util
import json
import tempfile
import subprocess
from unittest.mock import patch
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skill_eval', ROOT / 'evals/run.py')
evals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evals)


class SkillEvalTests(unittest.TestCase):
    def setUp(self):
        self.cases = evals.read_cases(ROOT / 'evals/cases.jsonl')
        self.case = next(c for c in self.cases if c['id'] == 'DELIVER-03')
        self.decision = {'skill': 'plane-deliver', 'actions': ['record_partial_acceptance'],
                         'rationale': 'Only the named criterion is accepted.'}

    def test_correct_partial_acceptance_plan_passes(self):
        self.assertTrue(evals.score(self.case, self.decision)['passed'])

    def test_unsafe_extra_action_fails_even_with_required_action(self):
        self.decision['actions'].append('merge_pr')
        result = evals.score(self.case, self.decision)
        self.assertFalse(result['passed'])
        self.assertTrue(result['critical_failure'])
        self.assertEqual(result['forbidden_decisions'], ['merge_pr'])

    def test_wrong_route_or_missing_decision_cannot_pass(self):
        for edits in ({'skill': 'plane-setup'}, {'actions': []}):
            with self.subTest(edits=edits):
                value = {**self.decision, **edits}
                self.assertFalse(evals.score(self.case, value)['passed'])

    def test_unknown_duplicate_or_malformed_action_is_not_scored(self):
        for actions in (['made_up_action'], ['merge_pr', 'merge_pr'], 'record_partial_acceptance', [1]):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                evals.score(self.case, {**self.decision, 'actions': actions})

    def test_equivalent_handoff_labels_and_missing_handoff(self):
        case = next(c for c in self.cases if c['id'] == 'DELIVER-02')
        for action in ('handoff_runtime', 'report_handoff', None):
            decision = {'skill': 'plane-deliver', 'actions': list(case['required_decisions']),
                        'rationale': 'Task version verified, entry and resource boundary handed off.'}
            if action:
                decision['actions'].append(action)
            with self.subTest(action=action):
                self.assertEqual(evals.score(case, decision)['passed'], action is not None)

    def test_unrelated_request_requires_no_plane_skill(self):
        case = next(c for c in self.cases if c['id'] == 'SETUP-07')
        decision = {'skill': None, 'actions': ['answer_directly'], 'rationale': 'A language question.'}
        self.assertTrue(evals.score(case, decision)['passed'])
        decision['skill'] = 'plane-setup'
        self.assertFalse(evals.score(case, decision)['passed'])

    def test_invalid_case_rubrics_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'cases.jsonl'
            for failure in ('duplicate', 'overlap', 'unknown', 'missing'):
                cases = copy.deepcopy(self.cases[:1])
                if failure == 'duplicate':
                    cases.append(copy.deepcopy(cases[0]))
                elif failure == 'overlap':
                    cases[0]['forbidden_decisions'].append(cases[0]['required_decisions'][0])
                elif failure == 'unknown':
                    cases[0]['required_decisions'].append('not_in_vocabulary')
                else:
                    cases[0]['must_observe'] = []
                path.write_text(''.join(json.dumps(c) + '\n' for c in cases))
                with self.subTest(failure=failure), self.assertRaises(ValueError):
                    evals.read_cases(path)

    def test_timeout_is_unverified_and_preserves_partial_events(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(evals.subprocess, 'check_output', return_value='codex-cli test'), \
                patch.object(evals.subprocess, 'run', side_effect=subprocess.TimeoutExpired(
                    ['codex'], 1, output=b'{"type":"turn.started"}\n', stderr=b'timeout')):
            output = Path(temp)
            result = evals.run_case(self.case, ROOT / 'plugins/plane-for-codex', output, 'test', 1, 1)
            self.assertEqual(result['status'], 'unverified')
            self.assertNotIn('passed', result)
            self.assertIn('turn.started', (output / 'DELIVER-03-1/events.jsonl').read_text())

    def test_successful_cli_without_decision_is_unverified(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(evals.subprocess, 'check_output', return_value='codex-cli test'), \
                patch.object(evals.subprocess, 'run', return_value=subprocess.CompletedProcess(
                    ['codex'], 0, '{"type":"turn.completed"}\n', '')):
            result = evals.run_case(self.case, ROOT / 'plugins/plane-for-codex', Path(temp), 'test', 1, 1)
            self.assertEqual(result['status'], 'unverified')
            self.assertNotIn('passed', result)

    def test_absent_rationale_and_unknown_skill_are_not_scored(self):
        for edits in ({'rationale': ''}, {'skill': 'invented'}):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                evals.score(self.case, {**self.decision, **edits})
