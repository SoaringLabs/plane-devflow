"""The emitted candidate manifest must work only through an explicit test channel."""
import json
import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import test_product_upgrade as fixtures
from test_product_upgrade import releases, upgrades, plane_workflow, github_setup, command


class CandidateChannelTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.UpgradeRecoveryTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.UpgradeRecoveryTests.tearDownClass.__func__)
    setUp = fixtures.UpgradeRecoveryTests.setUp
    no_network = fixtures.UpgradeRecoveryTests.no_network

    def candidate_plan(self):
        target = releases.manifest(self.source, self.commit, candidate=True)
        preview = upgrades.plan(self.root, target, home=self.home, candidate_source=True)
        upgrades.plan(self.root, target, home=self.home, candidate_source=True,
                      expected_plan_id=preview['plan_id'], apply=True)
        return preview['plan_id']

    def test_candidate_manifest_requires_explicit_channel_and_binds_plan_identity(self):
        target = releases.manifest(self.source, self.commit, candidate=True)
        with self.assertRaisesRegex(ValueError, 'stable release'):
            upgrades.plan(self.root, target, home=self.home)
        plan_id = self.candidate_plan()
        with self.assertRaisesRegex(Exception, 'candidate-source staging'):
            upgrades.stage(self.root, plan_id, source=self.source, apply=True)
        with self.assertRaisesRegex(Exception, 'explicit local source'):
            upgrades.stage(self.root, plan_id, candidate_source=True, apply=True)
        result = upgrades.stage(self.root, plan_id, source=self.source, candidate_source=True, apply=True)
        self.assertEqual(result['validation_mode'], 'candidate_fixture')
        with self.assertRaisesRegex(Exception, 'candidate-source staging'):
            upgrades.stage(self.root, plan_id, apply=True)
        root, record = upgrades.read(self.root, plan_id)
        record['plan']['candidate_source'] = False
        upgrades.save(root, plan_id, record)
        with self.assertRaisesRegex(Exception, 'modified'):
            upgrades.read(root, plan_id)

    def test_candidate_can_stage_install_and_verify_without_becoming_a_stable_upgrade(self):
        config = fixtures.fixtures.config()
        config['sync'] = {'provider': 'native'}
        (self.root / '.plane-devflow.json').write_text(json.dumps(config))
        command(self.root, 'add', '.')
        command(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Native fixture')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        plan_id = self.candidate_plan()
        upgrades.stage(self.root, plan_id, source=self.source, candidate_source=True, apply=True)
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            upgrades.prepare_project(self.root, plan_id, apply=True)
        def installer(args, root):
            for name in releases.SKILLS:
                target = Path(root) / '.agents/skills' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(self.source / 'skills' / name, target)
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch.object(upgrades, 'run_installer', side_effect=installer):
            result = upgrades.install_local(self.root, plan_id, apply=True)
        self.assertEqual(result['local_installation'], 'verified')
        report = {'configuration_status': 'complete', 'checks': {'native_mapping_verified': True}}
        with patch.object(plane_workflow, 'run', side_effect=self.no_network), patch.object(github_setup, 'check', return_value=report):
            result = upgrades.verify_project(self.root, plan_id)
        self.assertEqual(result['status'], 'candidate_complete')
        self.assertEqual(result['validation_mode'], 'candidate_fixture')

    def test_cli_exposes_explicit_candidate_arguments(self):
        helper = fixtures.ROOT / 'plugins/plane-devflow/scripts/plane_workflow.py'
        result = subprocess.run(['python3', str(helper), 'upgrade', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--candidate-source', result.stdout)
        self.assertIn('--source', result.stdout)
        release_file = Path(self.temp.name) / 'candidate.json'
        release_file.write_text(json.dumps(releases.manifest(self.source, self.commit, candidate=True)))
        with patch.object(upgrades, 'plan', return_value={'status': 'planned'}) as planner, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(plane_workflow.main(['upgrade', '--repo', str(self.root), '--step', 'plan',
                                                  '--release-file', str(release_file), '--candidate-source']), 0)
        self.assertTrue(planner.call_args.kwargs['candidate_source'])
        with patch.object(upgrades, 'stage', return_value={'status': 'staged'}) as staging, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(plane_workflow.main(['upgrade', '--repo', str(self.root), '--step', 'stage', '--plan-id', 'a' * 64,
                                                  '--source', str(self.source), '--candidate-source', '--apply']), 0)
        self.assertEqual(staging.call_args.kwargs, {'source': str(self.source), 'candidate_source': True, 'apply': True})


if __name__ == '__main__':
    unittest.main()
