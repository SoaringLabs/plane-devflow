"""Credential onboarding binds the repository and never transports PAT values."""
import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

import test_github_setup as fixtures
import plane_workflow as workflow
import plane_sync as sync


class CredentialGuideTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def test_plane_before_github_guidance_is_read_only_and_has_no_fake_pat_url(self):
        before = (self.root / sync.CONFIG_NAME).read_bytes()
        real_run = workflow.run
        calls = []
        def local_run(args, *pos, **kw):
            calls.append(args)
            return real_run(args, *pos, **kw)
        with patch.object(workflow, 'run', side_effect=local_run):
            plane = workflow.credential_guide(self.root, step='plane')
            github = workflow.credential_guide(self.root, step='github')
        self.assertTrue(all(args[0] == 'git' for args in calls))
        self.assertEqual(plane['url'], 'https://app.plane.so/example-workspace/')
        self.assertEqual(plane['next_step'], 'github')
        self.assertEqual(plane['suggested_title'], 'Plane DevFlow: example/demo-project')
        self.assertEqual(github['url'], 'https://github.com/example/demo-project/settings/secrets/actions/new')
        self.assertEqual(github['name_field'], 'PLANE_API_KEY')
        self.assertEqual(github['next_step'], 'verify')
        self.assertEqual((self.root / sync.CONFIG_NAME).read_bytes(), before)
        self.assertFalse(plane['writes_performed'] or github['writes_performed'])

    def test_verify_reads_metadata_only_and_does_not_fabricate_connection(self):
        real_run = workflow.run
        calls = []
        def fake_run(args, *pos, **kw):
            if args[0] != 'gh':
                return real_run(args, *pos, **kw)
            calls.append(args)
            data = [{'name':'PLANE_API_KEY', 'updatedAt':'2026-10-10T00:00:00Z', 'ignored':'not-a-real-token'}]
            return subprocess.CompletedProcess(args, 0, json.dumps(data), '')
        with patch.object(workflow, 'run', side_effect=fake_run):
            result = workflow.credential_guide(self.root, step='verify')
        self.assertEqual(calls, [['gh','secret','list','--repo','example/demo-project','--json','name,updatedAt']])
        self.assertTrue(result['secret_present'])
        self.assertEqual(result['next_step'], 'activation')
        self.assertFalse(result['credential_value_read'])
        self.assertNotIn('not-a-real-token', json.dumps(result))
        self.assertNotIn('connection_verified', result)

    def test_missing_secret_returns_to_storage_without_creating_another_pat(self):
        real_run = workflow.run
        def fake_run(args, *pos, **kw):
            if args[0] == 'gh':
                return subprocess.CompletedProcess(args, 0, '[]', '')
            return real_run(args, *pos, **kw)
        with patch.object(workflow, 'run', side_effect=fake_run):
            result = workflow.credential_guide(self.root, step='verify')
        self.assertFalse(result['secret_present'])
        self.assertEqual(result['next_step'], 'local')

    def test_permission_failure_is_not_reported_as_missing_or_ready(self):
        real_run = workflow.run
        def fake_run(args, *pos, **kw):
            if args[0] == 'gh':
                raise sync.WorkflowError('GitHub permission unavailable')
            return real_run(args, *pos, **kw)
        with patch.object(workflow, 'run', side_effect=fake_run):
            with self.assertRaisesRegex(sync.WorkflowError, 'permission'):
                workflow.credential_guide(self.root, step='verify')

    def test_native_never_requests_a_pat_or_calls_secrets(self):
        cfg = fixtures.config()
        cfg['sync'] = {'provider':'native'}
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(cfg))
        real_run = workflow.run
        def local_only(args, *pos, **kw):
            self.assertNotEqual(args[0], 'gh')
            return real_run(args, *pos, **kw)
        with patch.object(workflow, 'run', side_effect=local_only):
            for step in ['plane','github','verify']:
                self.assertEqual(workflow.credential_guide(self.root, step=step)['status'], 'skipped')

    def test_changed_origin_prevents_sending_credentials_to_stale_repository(self):
        workflow.run(['git','remote','set-url','origin','https://github.com/other/repository.git'], self.root)
        with self.assertRaisesRegex(sync.WorkflowError, 'origin'):
            workflow.credential_guide(self.root, step='github')

    def test_cli_current_step_without_credentials(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = workflow.main(['credential-guide','--repo',str(self.root),'--step','github'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['repository'], 'example/demo-project')

    def test_missing_secret_readiness_checks_local_reuse_before_pat_creation(self):
        import github_setup
        result = github_setup.assess(fixtures.config(), online={'secret_present':False})
        self.assertEqual(result['credential_step'], 'local')
        unknown = github_setup.assess(fixtures.config())
        self.assertIsNone(unknown['credential_step'])
        plan = github_setup.install(self.root, release=__import__("test_product_upgrade").release_fixture())
        self.assertEqual(plan['credential_guide_command'][-2:], ['--step','local'])
        self.assertIn(str(self.root), plan['credential_guide_command'])
