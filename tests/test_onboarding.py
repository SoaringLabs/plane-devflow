"""Recovery across missing tools, permissions, interruptions and stale evidence."""
import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

import test_github_setup as fixtures
import onboarding
import github_setup
import plane_sync
import plane_workflow
import setup_errors


class CapabilityTests(unittest.TestCase):
    def test_manual_flow_needs_no_tools_apps_or_accounts(self):
        with patch.object(onboarding.shutil, 'which', return_value=None):
            data = onboarding.capabilities()
        self.assertEqual(data['guidance_route'], 'manual-links')
        self.assertFalse(data['plane_desktop_required'])
        self.assertFalse(data['github_cli'])
        self.assertTrue(data['manual_guidance_available'])
        self.assertEqual(data['authentication'], 'unknown_until_service_probe')

    def test_each_host_surface_and_fallback_is_independent(self):
        for surfaces, expected in [(['browser-control','app-control'], 'browser-control'),
                                   (['app-control'], 'app-control'), (['url-opener'], 'url-opener'),
                                   ([], 'manual-links')]:
            with self.subTest(surfaces=surfaces):
                self.assertEqual(onboarding.capabilities(surfaces)['guidance_route'], expected)
        with self.assertRaises(plane_sync.WorkflowError):
            onboarding.capabilities(['private-plugin-import'])

    def test_cli_without_repository_reports_capabilities_only(self):
        output = io.StringIO()
        with patch.object(plane_workflow, 'run', side_effect=AssertionError('No Git/account calls')), contextlib.redirect_stdout(output):
            self.assertEqual(plane_workflow.main(['setup-capabilities']), 0)
        self.assertEqual(json.loads(output.getvalue())['guidance_route'], 'manual-links')


class RecoveryTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def report(self, **changes):
        evidence = fixtures.ReadinessTests().evidence()
        evidence.update(changes)
        return github_setup.assess(fixtures.config(), online=evidence)

    def run_progress(self, report, **options):
        with patch.object(onboarding.shutil, 'which', return_value='/test/gh'), patch.object(onboarding, 'check', return_value=report):
            return onboarding.progress(self.root, **options)

    def test_read_only_progress_leaves_no_checkpoint(self):
        data = self.run_progress(self.report(secret_present=False))
        self.assertEqual(data['next_step'], 'local_credential')
        self.assertFalse(onboarding.Path(data['checkpoint_path']).exists())

    def test_interrupt_after_pat_creation_resumes_at_storage_confirmation(self):
        report = self.report(secret_present=False)
        self.run_progress(report, event='pat-ready', apply=True)
        resumed = self.run_progress(report)
        self.assertEqual(resumed['recovery'], 'resumed')
        self.assertEqual(resumed['next_step'], 'confirm_pat_available_then_github')
        self.assertEqual(resumed['credential_guide']['step'], 'github')
        self.assertIsNone(resumed['event_writeback_verified'])
        saved = json.loads(onboarding.Path(resumed['checkpoint_path']).read_text())
        self.assertEqual(saved['reported_step'], 'pat-ready')
        self.assertEqual(set(saved), {'version','config_sha256','reported_step','observed_at','remote_checks'})

    def test_user_save_confirmation_does_not_claim_verified_storage(self):
        self.run_progress(self.report(secret_present=False), event='secret-saved', apply=True)
        data = self.run_progress(self.report(secret_present=False))
        self.assertEqual(data['next_step'], 'check_secret_repository_name_and_scope')
        self.assertEqual(data['readiness']['initialization'], 'partial')
        self.assertEqual(data['credential_guide']['step'], 'github')

    def test_lost_pat_checks_local_reuse_before_creation(self):
        self.run_progress(self.report(secret_present=False), event='pat-ready', apply=True)
        data = self.run_progress(self.report(secret_present=False), event='pat-unavailable', apply=True)
        self.assertEqual(data['next_step'], 'local_credential')

    def test_cached_success_is_never_proof_after_offline_restart(self):
        self.run_progress(self.report(), apply=True)
        data = onboarding.progress(self.root, offline=True)
        self.assertEqual(data['recovery'], 'resumed')
        self.assertEqual(data['readiness']['initialization'], 'partial')
        self.assertIsNone(data['readiness']['checks']['connection_verified'])
        self.assertFalse(data['cached_checks_reused_as_proof'])

    def test_online_restart_rechecks_current_evidence(self):
        self.run_progress(self.report(), apply=True)
        data = self.run_progress(self.report(connection_verified=False))
        self.assertEqual(data['next_step'], 'run_connection_check')
        self.assertEqual(data['readiness']['initialization'], 'partial')
        self.assertNotIn('credential_guide', data)

    def test_changed_config_uses_new_checkpoint_and_preserves_old(self):
        initial = self.run_progress(self.report(), event='pat-ready', apply=True)
        before = onboarding.Path(initial['checkpoint_path']).read_bytes()
        cfg = fixtures.config()
        cfg['sync'] = {'provider':'actions','api_version':'v2'}
        (self.root / plane_sync.CONFIG_NAME).write_text(json.dumps(cfg))
        new = onboarding.progress(self.root, offline=True, apply=True)
        self.assertNotEqual(new['checkpoint_path'], initial['checkpoint_path'])
        self.assertIsNone(new['reported_step'])
        self.assertEqual(onboarding.Path(initial['checkpoint_path']).read_bytes(), before)

    def test_wrong_origin_prevents_guidance_and_progress_write(self):
        plane_workflow.run(['git','remote','set-url','origin','https://github.com/other/repo.git'], self.root)
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'origin'):
            onboarding.progress(self.root, offline=True, apply=True)

    def test_corrupt_checkpoint_reconstructs_without_echo_or_overwrite(self):
        data = onboarding.progress(self.root, offline=True, apply=True)
        destination = onboarding.Path(data['checkpoint_path'])
        destination.write_text('private-string-not-to-echo')
        recovered = onboarding.progress(self.root, offline=True)
        self.assertEqual(recovered['recovery'], 'invalid')
        self.assertNotIn('private-string', json.dumps(recovered))
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'Checkpoint is invalid'):
            onboarding.progress(self.root, offline=True, apply=True)
        self.assertEqual(destination.read_text(), 'private-string-not-to-echo')

    def test_checkpoint_symlink_cannot_read_or_replace_unrelated_file(self):
        data = onboarding.progress(self.root, offline=True, apply=True)
        destination = onboarding.Path(data['checkpoint_path'])
        destination.unlink()
        target = self.root / 'unrelated'
        target.write_text('keep')
        destination.symlink_to(target)
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'symlink'):
            onboarding.progress(self.root, offline=True, apply=True)
        self.assertEqual(target.read_text(), 'keep')

    def test_missing_gh_keeps_manual_storage_and_partial_verification(self):
        with patch.object(onboarding.shutil, 'which', return_value=None), patch.object(onboarding, 'check', side_effect=AssertionError('No probe')):
            data = onboarding.progress(self.root)
        self.assertEqual(data['next_step'], 'verify_secret_metadata')
        self.assertEqual(data['credential_guide']['step'], 'github')
        self.assertIn('manual_storage_option', data)
        self.assertEqual(data['readiness']['initialization'], 'partial')

    def test_native_skips_gh_pat_and_secret_even_without_ui(self):
        cfg = fixtures.config()
        cfg['sync'] = {'provider':'native'}
        (self.root / plane_sync.CONFIG_NAME).write_text(json.dumps(cfg))
        real_run = plane_workflow.run
        def local(args, *pos, **kw):
            self.assertNotEqual(args[0], 'gh')
            return real_run(args, *pos, **kw)
        with patch.object(plane_workflow, 'run', side_effect=local):
            data = onboarding.progress(self.root, apply=True)
        self.assertEqual(data['next_step'], 'verify_native_mapping')
        self.assertNotIn('credential_guide', data)
        with self.assertRaises(plane_sync.WorkflowError):
            onboarding.progress(self.root, event='pat-ready', apply=True)

    def test_cli_checkpoint_survives_another_process(self):
        script = fixtures.ROOT / 'plugins/plane-devflow/scripts/plane_workflow.py'
        command = ['python3', str(script), 'setup-progress', '--repo', str(self.root), '--offline']
        saved = json.loads(plane_workflow.run(command + ['--event','pat-ready','--apply']).stdout)
        resumed = json.loads(plane_workflow.run(command).stdout)
        self.assertTrue(saved['checkpoint_written'])
        self.assertEqual(resumed['reported_step'], 'pat-ready')
        self.assertEqual(resumed['recovery'], 'resumed')
        self.assertFalse(resumed['checkpoint_written'])

    def test_concurrent_progress_change_blocks_overwrite(self):
        first = onboarding.progress(self.root, offline=True, apply=True)
        destination = onboarding.Path(first['checkpoint_path'])
        original = onboarding.receipt
        calls = 0
        def read_then_change(path, digest):
            nonlocal calls
            data, status = original(path, digest)
            calls += 1
            if calls == 1:
                updated = dict(data, reported_step='secret-saved')
                destination.write_text(json.dumps(updated))
            return data, status
        with patch.object(onboarding, 'receipt', side_effect=read_then_change):
            with self.assertRaisesRegex(plane_sync.WorkflowError, 'concurrently'):
                onboarding.progress(self.root, offline=True, event='pat-ready', apply=True)
        self.assertEqual(json.loads(destination.read_text())['reported_step'], 'secret-saved')

    def test_permissions_network_and_actions_blockers_do_not_generate_pat(self):
        cases = [('permission_denied','resolve_permissions'), ('authentication_required','login_github'),
                 ('rate_limited','retry_checks_later'), ('network_unavailable','retry_checks_later')]
        for code, expected in cases:
            report = self.report(secret_present=None)
            report['issues'] = [setup_errors.issue(code, 'secret_metadata')]
            data = self.run_progress(report)
            self.assertEqual(data['next_step'], expected)
            self.assertNotIn('credential_guide', data)
        data = self.run_progress(self.report(actions_enabled=False, secret_present=False))
        self.assertEqual(data['next_step'], 'enable_actions')


class SafeProbeTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def test_errors_stay_unknown_and_never_echo_response(self):
        for status, expected in [(401,'authentication_required'), (403,'permission_denied'),
                                 (404,'not_found_or_hidden'), (429,'rate_limited'), (503,'network_unavailable')]:
            real_run = plane_workflow.run
            def fake(args, *pos, **kw):
                if args[0] == 'gh':
                    return subprocess.CompletedProcess(args, 1, '', f'HTTP {status} private-response-token')
                return real_run(args, *pos, **kw)
            with patch.object(plane_workflow, 'run', side_effect=fake):
                result = github_setup.check(self.root)
            self.assertEqual(result['issues'][0]['code'], expected)
            self.assertIsNone(result['checks']['secret_present'])
            self.assertIsNone(result['checks']['remote_files_match'])
            self.assertIsNone(result['checks']['remote_config_matches'])
            self.assertIsNone(result['checks']['connection_verified'])
            self.assertNotIn('private-response-token', json.dumps(result))

    def test_invalid_response_stays_unknown(self):
        with patch.object(plane_workflow, 'run', return_value=subprocess.CompletedProcess([], 0, 'not-json-sensitive', '')):
            with self.assertRaises(setup_errors.ProbeError) as context:
                setup_errors.github_json(['gh','api','example'], self.root, 'repository')
        self.assertEqual(context.exception.issue['code'], 'invalid_response')
        self.assertNotIn('sensitive', str(context.exception))

    def test_cli_timeout_is_bounded_and_safe(self):
        with patch.object(plane_workflow.subprocess, 'run', side_effect=subprocess.TimeoutExpired('gh',30,output='private-token')):
            with self.assertRaisesRegex(plane_sync.WorkflowError, 'timed out') as context:
                plane_workflow.run(['gh','api','example'])
        self.assertNotIn('private-token', str(context.exception))
