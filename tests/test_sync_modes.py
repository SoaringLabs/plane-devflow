"""Release 0.4 routing and provider boundaries through real local HTTP and Git."""
import copy
import json
import os
import sys
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import test_github_setup as setup_tests
from test_workflow import config, event, MemoryPlane
import plane_sync as sync
import action_runner as runner
import github_setup as setup


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.cfg['completion']['policy'] = 'on_merge'
        self.item = MemoryPlane(self.cfg).item
        self.item.update(project=self.item.pop('project_id'), state=self.cfg['states']['in_progress'])
        self.item.pop('state_id')
        self.item['labels'] = ['label-uuid']
        self.group = 'started'
        self.label = 'manual-acceptance'
        self.requests, self.comments, self.states = [], {}, []
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def handle_request(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
                fixture.requests.append((self.command, self.path, body))
                path = self.path.split('?')[0]
                if self.command == 'GET' and '/work-items/DEMO-' in path:
                    data = copy.deepcopy(fixture.item)
                    if '/api/v2/' in path:
                        data = dict(data, project_id=data.pop('project'), state_id=data['state'], state={'id': data['state'], 'group': 'started'}, labels=[])
                elif self.command == 'GET' and path.endswith('/states/'):
                    data = [{'id': fixture.item['state'], 'group': fixture.group}]
                elif self.command == 'GET' and path.endswith('/labels/'):
                    data = [{'id': 'label-uuid', 'name': fixture.label}]
                elif self.command == 'PATCH':
                    key = 'state_id' if '/api/v2/' in path else 'state'
                    fixture.item['state'] = body[key]
                    fixture.states.append(body[key])
                    data = fixture.item
                elif self.command == 'POST' and '/api/v2/' in path and path.endswith('/comments/upsert/'):
                    fixture.comments[body['external_id']] = body
                    data = {'id': 'comment-uuid'}
                else:
                    self.send_error(404)
                    return
                payload = json.dumps(data).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            do_GET = do_PATCH = do_POST = handle_request
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.cfg['plane']['api_url'] = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def client(self):
        return sync.PlaneClient(self.cfg, 'local-test-fixture', allow_localhost=True)

    def test_v1_defaults_normalize_labels_and_manual_merge_preserves_review(self):
        client = self.client()
        result = sync.sync_event(event(merged=True, state='closed'), self.cfg, client)
        sync.sync_event(event(merged=True, state='closed'), self.cfg, client)
        self.assertTrue(result['manual_acceptance'])
        self.assertEqual(self.states, [self.cfg['states']['in_review']])
        self.assertEqual(len(self.comments), 1)
        self.assertTrue(all('/api/v1/' in path for method, path, _ in self.requests if method in {'GET', 'PATCH'}))
        self.assertTrue(all('/api/v2/' in path for method, path, _ in self.requests if method == 'POST'))

    def test_terminal_state_resolved_without_expansion_cannot_regress(self):
        self.group = 'cancelled'
        sync.sync_event(event(), self.cfg, self.client())
        self.assertEqual(self.states, [])

    def test_explicit_v2_uses_v1_guard_against_stale_relation_reads(self):
        self.cfg['sync'] = {'provider': 'actions', 'api_version': 'v2'}
        result = sync.sync_event(event(merged=True), self.cfg, self.client())
        self.assertTrue(result['manual_acceptance'])
        patches = [(p, b) for m, p, b in self.requests if m == 'PATCH']
        self.assertIn('/api/v2/', patches[0][0])
        self.assertEqual(patches[0][1], {'state_id': self.cfg['states']['in_review']})
        self.assertTrue(any('/api/v1/' in p and '/work-items/DEMO-' in p for m,p,b in self.requests))

    def test_unresolvable_manual_label_fails_before_mutations(self):
        self.item['labels'] = ['not-returned']
        with self.assertRaisesRegex(sync.WorkflowError, 'acceptance labels'):
            sync.sync_event(event(merged=True), self.cfg, self.client())
        self.assertFalse(self.states or self.comments)

    def test_wrong_project_rejected_before_relation_reads(self):
        self.item['project'] = 'wrong-project'
        with self.assertRaises(sync.WorkflowError):
            sync.sync_event(event(), self.cfg, self.client())
        self.assertEqual(len(self.requests), 1)


class ProviderTests(unittest.TestCase):
    def native(self):
        cfg = config()
        cfg['sync'] = {'provider': 'native', 'api_version': 'v1'}
        return cfg

    def test_native_event_no_client_needed_and_no_mutations(self):
        self.assertEqual(sync.sync_event(event(), self.native())['reason'], 'native_provider_owns_pr_events')
        self.assertFalse(sync.state_sync_enabled(self.native()))
        self.assertTrue(sync.state_sync_enabled(config()))

    def test_native_action_does_not_construct_plane_client_without_secret(self):
        with patch.object(runner, 'fetch_config', return_value=self.native()), patch.object(runner, 'github_snapshot', side_effect=lambda e,t:e), patch.object(runner, 'PlaneClient') as client:
            result = runner.run_action(event(), 'example/demo-project', 'github-fixture', None)
        self.assertEqual(result['status'], 'skipped')
        client.assert_not_called()

    def test_native_cannot_fake_readiness_with_successful_actions_checks(self):
        result = setup.assess(self.native(), online={k: True for k in ['actions_enabled','workflow_active','remote_files_match','remote_config_matches','secret_present','connection_verified']})
        self.assertEqual(result['initialization'], 'partial')
        self.assertFalse(result['secret_required'])

    def test_reject_invalid_mode_version_or_embedded_credentials(self):
        for settings in [{'provider':'none'}, {'api_version':'v3'}, {'token':'secret'}, []]:
            cfg = config()
            cfg['sync'] = settings
            with self.assertRaises(sync.WorkflowError):
                sync.validate_config(cfg)


class UpgradeTests(unittest.TestCase):
    setUp = setup_tests.RepositoryTests.setUp
    def test_reviewed_upgrade_backs_up_original_bytes_and_preserves_config(self):
        setup.install(self.root, apply=True)
        old = self.root / setup.BUNDLE / 'plane_sync.py'
        old.write_text('previous-reviewed-version')
        before = (self.root / sync.CONFIG_NAME).read_bytes()
        plan = setup.install(self.root, upgrade=True)
        with self.assertRaises(sync.WorkflowError):
            setup.install(self.root, apply=True, upgrade=True)
        result = setup.install(self.root, apply=True, upgrade=True, expected_files_sha256=plan['expected_files_sha256'])
        self.assertEqual((Path(result['backup']) / setup.BUNDLE / 'plane_sync.py').read_text(), 'previous-reviewed-version')
        self.assertEqual((self.root / sync.CONFIG_NAME).read_bytes(), before)
        self.assertEqual(old.read_bytes(), setup.bundled_files()[setup.BUNDLE + '/plane_sync.py'])

    def test_upgrade_stale_manifest_cannot_overwrite(self):
        setup.install(self.root, apply=True)
        path = self.root / setup.BUNDLE / 'plane_sync.py'
        path.write_text('old')
        plan = setup.install(self.root, upgrade=True)
        path.write_text('new-unrelated-change')
        with self.assertRaises(sync.WorkflowError):
            setup.install(self.root, upgrade=True, apply=True, expected_files_sha256=plan['expected_files_sha256'])
        self.assertEqual(path.read_text(), 'new-unrelated-change')

    def test_native_install_skips_files_and_evidence_binds_exact_configuration(self):
        cfg = config()
        cfg['sync'] = {'provider':'native'}
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(cfg))
        self.assertEqual(setup.install(self.root, apply=True)['files'], [])
        self.assertFalse((self.root / setup.WORKFLOW).exists())
        evidence = dict(config_sha256=setup.config_digest(cfg), workspace=cfg['plane']['workspace'], project_id=cfg['plane']['project_id'], repository=cfg['github']['repository'], repository_mapped=True, workflow_rules_verified=True, overlapping_actions_disabled=True, source='user_confirmation', observed_at=datetime.now(timezone.utc).isoformat())
        receipt = self.root / 'observation.json'
        receipt.write_text(json.dumps(evidence))
        bad = dict(evidence, overlapping_actions_disabled=False)
        with self.assertRaises(sync.WorkflowError):
            setup.validate_native_evidence(cfg, bad)
        setup.record_native(self.root, receipt, apply=True)
        import plane_workflow as workflow
        real_run = workflow.run
        def local_only(args, *pos, **kw):
            self.assertNotEqual(args[0], 'gh', 'Native check must not inspect Actions or Secrets')
            return real_run(args, *pos, **kw)
        with patch.object(workflow, 'run', side_effect=local_only):
            result = setup.check(self.root)
        self.assertEqual(result['initialization'], 'complete')
        self.assertEqual(result['evidence']['source'], 'user_confirmation')
        cfg['completion']['policy'] = 'on_merge'
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(cfg))
        self.assertEqual(setup.check(self.root)['initialization'], 'partial')


class ConfigureModeTests(unittest.TestCase):
    import test_setup as fixtures
    setUp = fixtures.SetupTests.setUp
    git = fixtures.SetupTests.git
    args = fixtures.SetupTests.args

    def test_new_native_mapping_and_same_project_rerun_preserve_mode(self):
        import plane_workflow as workflow
        plan = workflow.configure(self.args(sync_provider='native'))
        self.assertEqual(plan['config']['sync'], {'provider':'native','api_version':'v1'})
        workflow.configure(self.args(sync_provider='native', apply=True))
        before = self.path.read_bytes()
        workflow.configure(self.args(apply=True))
        self.assertEqual(self.path.read_bytes(), before)

    def test_explicit_compatibility_defaults_do_not_force_legacy_mapping_change(self):
        import plane_workflow as workflow
        self.path.write_text(json.dumps(config()))
        before = self.path.read_bytes()
        plan = workflow.configure(self.args(sync_provider='actions', api_version='v1', apply=True))
        self.assertFalse(plan['changed'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_provider_change_preserves_targets_and_requires_reviewed_hash(self):
        import plane_workflow as workflow
        self.path.write_text(json.dumps(config()))
        plan = workflow.configure(self.args(sync_provider='native', replace=True))
        self.assertEqual(plan['config']['states'], config()['states'])
        with self.assertRaises(sync.WorkflowError):
            workflow.configure(self.args(sync_provider='native', replace=True, apply=True))
        workflow.configure(self.args(sync_provider='native', replace=True, apply=True, expected_config_sha256=plan['expected_config_sha256']))
        self.assertFalse(sync.state_sync_enabled(sync.read_config(self.path)))

    def test_new_project_preserves_provider_but_clears_old_state_targets(self):
        import plane_workflow as workflow
        cfg = config()
        cfg['sync'] = {'provider':'native', 'api_version':'v1'}
        self.path.write_text(json.dumps(cfg))
        other = '66666666-6666-4666-8666-666666666666'
        self.project.write_text(json.dumps({'id': other, 'identifier':'OTHER'}))
        plan = workflow.configure(self.args(project_id=other, project_key='OTHER', replace=True))
        self.assertEqual(plan['config']['states'], {})
        self.assertEqual(plan['config']['sync'], cfg['sync'])
