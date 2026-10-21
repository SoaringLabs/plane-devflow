#!/usr/bin/env python3
"""Explicit macOS vault smoke test with one unique synthetic entry and cleanup.

Uses the production native adapter and human-command paths, with synthetic input
and a stubbed GitHub CLI sink. No real PAT, GitHub call, or existing credential
is involved. Requires --run; ordinary test discovery never executes this file.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/plane-devflow/scripts'))
import credential_store as vault
import plane_workflow as workflow
from plane_sync import CONFIG_NAME, WorkflowError, require


def run_smoke(run_id):
    account = 'synthetic-smoke-' + str(uuid.UUID(run_id))
    first, replacement = 'synthetic-first-' + run_id, 'synthetic-replacement-' + run_id
    config = json.loads((ROOT / 'examples/plane-devflow.basic.json').read_text())
    config['plane'].update(api_url='https://plane-devflow-smoke.invalid',
                           app_url='https://plane-devflow-smoke.invalid', workspace='credential-smoke')
    scope = vault.Scope.from_config(config, account)
    store = vault.MacKeychain(scope)
    report = {'platform': sys.platform, 'test_scope': scope.metadata(), 'test_entry': scope.key,
              'github_network_called': False, 'real_pat_used': False, 'checks': [],
              'cleanup': 'not_needed', 'status': 'running'}
    owned = False
    stage = 'initial_presence'

    def check(condition, name):
        require(condition, 'Native smoke check failed: ' + name)
        report['checks'].append(name)

    def selected_store(candidate):
        require(candidate == scope, 'Smoke test refused a credential outside its synthetic scope.')
        return vault.MacKeychain(candidate)

    try:
        # Read only this unpredictable synthetic scope before taking ownership.
        require(not store.contains(), 'Synthetic test entry already exists; choose a fresh run ID.')
        owned = True
        check(True, 'initial_entry_missing')
        with tempfile.TemporaryDirectory(prefix='plane-credential-smoke-') as temp:
            repos = []
            for index, owner in enumerate(('credential-smoke-a', 'credential-smoke-b')):
                path = Path(temp) / str(index)
                path.mkdir()
                repository = owner + '/sample'
                workflow.run(['git', 'init', '-b', 'main'], path)
                workflow.run(['git', 'remote', 'add', 'origin', 'https://github.com/' + repository + '.git'], path)
                mapped = json.loads(json.dumps(config))
                mapped['github']['repository'] = repository
                # Distinct Plane project, same account/workspace credential.
                mapped['plane']['project_id'] = str(uuid.uuid4())
                (path / CONFIG_NAME).write_text(json.dumps(mapped))
                repos.append((path, mapped))

            a, b = repos[0][0], repos[1][0]
            real_run = workflow.run
            uploaded = []

            def transport(args, *pos, **kw):
                if args[0] != 'gh':
                    return real_run(args, *pos, **kw)
                if args[1:3] == ['secret', 'list']:
                    return subprocess.CompletedProcess(args, 0, '[]', '')
                require(args == ['gh', 'secret', 'set', 'PLANE_API_KEY', '--repo', 'credential-smoke-b/sample'],
                        'Smoke test refused an unexpected GitHub operation.')
                check(kw.get('input_text') in (first, replacement), 'synthetic_value_sent_via_stdin')
                check(all(first not in arg and replacement not in arg for arg in args), 'no_token_in_arguments')
                uploaded.append(kw['input_text'])
                return subprocess.CompletedProcess(args, 0, '', '')

            with patch.object(vault, 'open_store', side_effect=selected_store), \
                 patch.object(workflow.sys.stdin, 'isatty', return_value=True), \
                 patch.object(workflow, 'run', side_effect=transport):
                stage = 'remember'
                with patch.object(workflow.getpass, 'getpass', return_value=first):
                    result = workflow.local_credential(a, account=account, action='remember', apply=True)
                check(result['status'] == 'remembered', 'remember_in_native_keychain')
                stage = 'presence'
                check(workflow.local_credential(b, account=account)['saved'] is True, 'presence_from_second_repository')
                stage = 'reuse'
                with patch('builtins.input', return_value='credential-smoke-b/sample'):
                    result = workflow.set_secret(b, account=account, use_saved=True)
                check(uploaded == [first] and result['source'] == 'local_system_store', 'reuse_across_github_owners_and_plane_projects')
                check(first not in json.dumps(result), 'no_token_in_result')

                stage = 'replacement_guard'
                with patch.object(workflow.getpass, 'getpass', side_effect=AssertionError('Unexpected PAT prompt')):
                    try:
                        workflow.local_credential(a, account=account, action='remember', apply=True)
                    except WorkflowError:
                        check(True, 'implicit_replacement_rejected')
                    else:
                        raise WorkflowError('Native smoke check failed: implicit replacement was permitted.')
                stage = 'explicit_replacement'
                with patch.object(workflow.getpass, 'getpass', return_value=replacement):
                    workflow.local_credential(a, account=account, action='remember', replace=True, apply=True)
                with patch('builtins.input', return_value='credential-smoke-b/sample'):
                    workflow.set_secret(b, account=account, use_saved=True)
                check(uploaded[-1] == replacement, 'explicit_replacement_read_back')

                stage = 'forget'
                with patch('builtins.input', return_value=account):
                    result = workflow.local_credential(a, account=account, action='forget', apply=True)
                check(result['status'] == 'forgotten' and not store.contains(), 'forget_and_verify_absent')
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', failed_stage=stage, error_type=type(error).__name__)
        # Only our deliberately safe WorkflowError text may cross this boundary.
        if isinstance(error, WorkflowError):
            report['error'] = str(error)
    finally:
        if owned:
            try:
                store.delete()  # Exact random test key only; repeated deletion is safe.
                require(not store.contains(), 'Synthetic test entry still exists.')
                report['cleanup'] = 'verified_absent'
            except Exception:
                report.update(status='failed', cleanup='pending_for_test_entry_only')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicitly allow the unique synthetic native Keychain test.')
    parser.add_argument('--run-id', type=uuid.UUID, default=uuid.uuid4(), help='Non-secret unique test ID for cleanup tracking.')
    args = parser.parse_args()
    if not args.run or sys.platform != 'darwin':
        parser.error('Run explicitly with --run on macOS. Windows native verification is not part of this test.')
    report = run_smoke(str(args.run_id))
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
