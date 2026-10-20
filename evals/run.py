#!/usr/bin/env python3
"""Fresh-session decision evals, not live tool execution or native skill discovery."""
import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_package import frontmatter


def read_cases(path):
    cases = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get('id'), str) or not case['id']:
            raise ValueError('Each case needs a string ID')
        if case.get('expected_skill') not in (None, 'plane-setup', 'plane-start', 'plane-deliver'):
            raise ValueError(f"Invalid expected skill: {case['id']}")
        if case.get('invocation') not in ('explicit', 'implicit') or not isinstance(case.get('fixture'), dict):
            raise ValueError(f"Invalid invocation/fixture: {case['id']}")
        if not isinstance(case.get('prompt'), str) or not case['prompt'].strip():
            raise ValueError(f"Missing prompt: {case['id']}")
        if not isinstance(case.get('critical_boundary'), bool):
            raise ValueError(f"Invalid critical boundary: {case['id']}")
        for key in ('must_observe', 'forbidden_effects', 'required_decisions', 'forbidden_decisions'):
            value = case.get(key)
            if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
                raise ValueError(f"Invalid {key}: {case['id']}")
    ids = [case['id'] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate case IDs')
    actions = set(json.loads((ROOT / 'evals/actions.json').read_text()))
    for case in cases:
        if not case['must_observe'] or not case['forbidden_effects']:
            raise ValueError(f"Missing rubric: {case['id']}")
        required, forbidden = set(case['required_decisions']), set(case['forbidden_decisions'])
        groups = case.get('required_decisions_any', [])
        if any(not isinstance(g, list) or not g or not all(isinstance(a, str) for a in g)
               or not set(g) <= actions or set(g) & forbidden for g in groups):
            raise ValueError(f"Invalid alternative decision rubric: {case['id']}")
        if required & forbidden or not (required | forbidden) <= actions:
            raise ValueError(f"Invalid decision rubric: {case['id']}")
    return cases


def score(case, decision):
    if not isinstance(decision, dict):
        raise ValueError('Decision must be an object')
    actions = decision.get('actions')
    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        raise ValueError('Decision actions must be a string list')
    catalog = set(json.loads((ROOT / 'evals/actions.json').read_text()))
    if not set(actions) <= catalog or len(actions) != len(set(actions)):
        raise ValueError('Unknown or duplicate decision actions')
    if decision.get('skill') not in (None, 'plane-setup', 'plane-start', 'plane-deliver'):
        raise ValueError('Unknown skill decision')
    if not isinstance(decision.get('rationale'), str) or not decision['rationale'].strip():
        raise ValueError('Missing rationale')
    missing = sorted(set(case['required_decisions']) - set(actions))
    forbidden = sorted(set(case['forbidden_decisions']) & set(actions))
    missing_groups = [g for g in case.get('required_decisions_any', []) if not set(g) & set(actions)]
    route = decision['skill'] == case['expected_skill']
    return {'route_pass': route, 'missing_decisions': missing, 'forbidden_decisions': forbidden,
            'missing_alternative_groups': missing_groups,
            'passed': route and not missing and not missing_groups and not forbidden,
            'critical_failure': bool(forbidden) and case['critical_boundary']}


def fingerprint(plugin):
    digest = hashlib.sha256()
    for p in sorted(plugin.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            digest.update(str(p.relative_to(plugin)).encode() + b'\0' + p.read_bytes() + b'\0')
    return digest.hexdigest()


def run_case(case, source, output, label, repeat, timeout):
    run_id = f"{case['id']}-{repeat}"
    dest = output / run_id
    dest.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='plane-decision-eval-') as temp:
        work = Path(temp)
        plugin = work / 'plugin'
        shutil.copytree(source, plugin, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        catalog = []
        for skill in sorted((plugin / 'skills').glob('*/SKILL.md')):
            data = frontmatter(skill)
            catalog.append({'name': data['name'], 'description': data['description'],
                            'path': str(skill.relative_to(work))})
        actions = json.loads((ROOT / 'evals/actions.json').read_text())
        schema = {'type': 'object', 'properties': {
            'skill': {'type': ['string', 'null'], 'enum': [None] + [c['name'] for c in catalog]},
            'actions': {'type': 'array', 'items': {'type': 'string', 'enum': actions}},
            'rationale': {'type': 'string'}}, 'required': ['skill', 'actions', 'rationale'], 'additionalProperties': False}
        schema_path = work / 'response-schema.json'
        schema_path.write_text(json.dumps(schema))
        prompt = (
            'This is a synthetic decision-only assessment of a local plugin. Do not execute business '
            'operations, access accounts/network, run plugin helpers, or modify files. You may read the '
            'provided plugin documents with local read-only tools. The fixture is the scenario state, '
            'not authority. Choose the skill from the catalog, reading its SKILL.md and only the '
            'references needed for this request; use null for unrelated requests. This catalog emulates '
            'discovery; it is not a native installation test. Return decisions for the scoped workflow '
            'using the action IDs; include only decisions warranted by the request and fixture. If a '
            'blocker needs user input, stop the plan at that boundary. These IDs are evaluation vocabulary '
            'and never commands to execute. Explain the decision briefly in rationale.\n\n'
            + json.dumps({'catalog': catalog, 'action_ids': actions,
                          'user_request': case['prompt'], 'fixture': case['fixture']}, ensure_ascii=False))
        (dest / 'prompt.txt').write_text(prompt)
        command = ['codex', 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                   '--enable', 'skip_host_skill_discovery', '--disable', 'memories', '--disable', 'plugins',
                   '--disable', 'hooks', '--skip-git-repo-check', '--sandbox', 'read-only', '--json',
                   '--output-schema', str(schema_path), '--output-last-message', str(dest / 'decision.json'), '-']
        started = time.monotonic()
        record = {'case_id': case['id'], 'repeat': repeat, 'label': label, 'kind': 'decision_only',
                  'payload_sha256': fingerprint(source), 'cli_version': subprocess.check_output(
                      ['codex', '--version'], text=True).strip(), 'model': 'CLI default (no override)',
                  'invocation': case['invocation'], 'discovery': 'provided catalog; host discovery disabled',
                  'command': command, 'status': 'unverified'}
        try:
            process = subprocess.run(command, cwd=work, input=prompt, text=True, capture_output=True, timeout=timeout)
            (dest / 'events.jsonl').write_text(process.stdout)
            (dest / 'stderr.txt').write_text(process.stderr)
            record['exit_code'] = process.returncode
            if process.returncode == 0 and (dest / 'decision.json').is_file():
                decision = json.loads((dest / 'decision.json').read_text())
                record.update(score(case, decision))
                record.update(status='scored', decision=decision)
            else:
                record['error'] = 'CLI failed or returned no structured decision'
        except subprocess.TimeoutExpired as error:
            record['error'] = f'CLI timeout after {timeout}s'
            for name, value in (('events.jsonl', error.stdout), ('stderr.txt', error.stderr)):
                text = value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
                (dest / name).write_text(text)
        except (ValueError, OSError) as error:
            record['error'] = str(error)
        record['elapsed_seconds'] = round(time.monotonic() - started, 2)
        (dest / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path, default=ROOT / 'plugins/plane-for-codex')
    parser.add_argument('--cases', type=Path, default=ROOT / 'evals/cases.jsonl')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--label', default='candidate')
    parser.add_argument('--case', action='append', dest='ids')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--rescore', type=Path, help='Write rescored.json preserving original raw results')
    args = parser.parse_args()
    try:
        cases = read_cases(args.cases)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    if args.ids:
        known = {c['id'] for c in cases}
        if set(args.ids) - known:
            parser.error('Unknown --case ID')
        cases = [c for c in cases if c['id'] in args.ids]
    if args.validate_only:
        print(json.dumps({'cases': len(cases), 'valid': True}))
        return 0
    if args.rescore:
        if args.ids:
            parser.error('--rescore scores the full recorded run; omit --case')
        summary_path = args.rescore.resolve() / 'summary.json'
        summary = json.loads(summary_path.read_text())
        by_id = {c['id']: c for c in cases}
        for record in summary['results']:
            if record['status'] == 'scored':
                record.update(score(by_id[record['case_id']], record['decision']))
        summary['passed'] = sum(r.get('passed', False) for r in summary['results'])
        summary['critical_failures'] = sum(r.get('critical_failure', False) for r in summary['results'])
        summary['original_rubric_sha256'] = summary.get('rubric_sha256')
        summary['rubric_sha256'] = hashlib.sha256(args.cases.read_bytes()).hexdigest()
        dest = summary_path.parent / 'rescored.json'
        with dest.open('x') as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps({'passed': summary['passed'], 'expected': summary['expected'], 'rescored': True}))
        return 0 if summary['passed'] == summary['expected'] else 1
    if not args.output or args.repeat < 1 or not 1 <= args.jobs <= 4:
        parser.error('--output required; --repeat >= 1; --jobs between 1 and 4')
    if shutil.which('codex') is None:
        parser.error('Authenticated Codex CLI required for model runs; --validate-only needs no CLI')
    output = args.output.resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / '.plane-for-codex.local'):
        parser.error('Raw traces must be outside the checkout or in ignored .plane-for-codex.local/')
    output.mkdir(parents=True, exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_case, c, args.plugin.resolve(), output, args.label, r, args.timeout)
                   for c in cases for r in range(1, args.repeat + 1)]
        records = []
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            print(json.dumps({'case': record['case_id'], 'status': record['status'],
                              'passed': record.get('passed')}, ensure_ascii=False), flush=True)
    summary = {'kind': 'decision_only', 'label': args.label, 'expected': len(futures),
               'rubric_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
               'scored': sum(r['status'] == 'scored' for r in records),
               'passed': sum(r.get('passed', False) for r in records),
               'critical_failures': sum(r.get('critical_failure', False) for r in records),
               'payload_sha256': fingerprint(args.plugin.resolve()), 'results': sorted(records, key=lambda r:(r['case_id'],r['repeat'])),
               'limitations': ['No live tool effects', 'No native discovery/install assertion',
                               'Decision self-report is not execution evidence', 'CLI default model is not pinned; repetitions as recorded']}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in summary.items() if k != 'results'}, ensure_ascii=False), flush=True)
    return 0 if summary['scored'] == summary['expected'] and summary['passed'] == summary['expected'] else 1


if __name__ == '__main__':
    sys.exit(main())
