"""Age and probe budgets apply across worktrees, successes and failures."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import test_github_setup as fixtures
import github_setup
import plane_sync
import plane_workflow
import sync_health

NOW = datetime(2026, 10, 22, 1, tzinfo=timezone.utc)


class HealthTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def report(self, when=NOW, passed=True):
        cfg = fixtures.config()
        online = fixtures.ReadinessTests().evidence()
        online['connection_verified'] = passed
        report = github_setup.assess(cfg, online=online)
        report['evidence'] = dict(online, connection_checked_at=when.isoformat(),
                                  connection_conclusion='success' if passed else 'failure')
        return github_setup.describe_health(report, cfg, now=NOW)

    def status(self, **kwargs):
        return sync_health.status(self.root, now=NOW, **kwargs)

    def test_age_boundary_missing_future_and_invalid(self):
        for value in (None, 'private-bad-time', NOW.replace(tzinfo=None).isoformat(), (NOW + timedelta(seconds=1)).isoformat()):
            self.assertEqual(github_setup.freshness(value, now=NOW), 'unknown')
        self.assertEqual(github_setup.freshness((NOW-timedelta(seconds=86399)).isoformat(), now=NOW), 'fresh')
        self.assertEqual(github_setup.freshness((NOW-timedelta(days=1)).isoformat(), now=NOW), 'expired')

    def test_expired_success_preserves_configuration_not_current_connection(self):
        data = github_setup.describe_health(self.report(NOW-timedelta(days=100)), fixtures.config(), now=NOW)
        self.assertEqual(data['configuration_status'], 'complete')
        self.assertEqual(data['github_sync'], 'stale')
        self.assertIsNone(data['checks']['connection_verified'])
        self.assertTrue(data['connection']['historical_result'])
        self.assertIsNone(data['event_writeback_verified'])

    def test_native_old_observation_requires_refresh(self):
        cfg = fixtures.config(); cfg['sync'] = {'provider':'native'}
        report = github_setup.assess(cfg, online={'native_mapping_verified':True})
        report['evidence'] = {'native_mapping_verified':True, 'source':'user_confirmation',
                              'observed_at':(NOW-timedelta(days=100)).isoformat()}
        data = github_setup.describe_health(report, cfg, now=NOW)
        self.assertEqual(data['github_sync'], 'stale')
        self.assertEqual(data['connection']['source'], 'user_confirmation')
        self.assertIsNone(data['checks']['native_mapping_verified'])

    def test_daily_probe_shared_by_worktrees_and_does_not_change_checkout(self):
        other = self.root.parent / (self.root.name + '-health-worktree')
        self.addCleanup(lambda: plane_workflow.run(['git','worktree','remove','--force',str(other)],self.root,check=False))
        plane_workflow.run(['git','add','.'],self.root)
        plane_workflow.run(['git','-c','user.name=Fixture','-c','user.email=test@example.invalid','commit','-m','fixture'],self.root)
        plane_workflow.run(['git','worktree','add','-b','other',str(other)],self.root)
        before = plane_workflow.run(['git','status','--porcelain'],self.root).stdout
        probe=Mock(return_value=self.report())
        first=self.status(persist=True,probe=probe)
        second=sync_health.status(other,now=NOW+timedelta(hours=23),persist=True,probe=probe)
        self.assertEqual(probe.call_count,1)
        self.assertEqual(second['observation']['source'],'cached')
        self.assertEqual(plane_workflow.run(['git','status','--porcelain'],self.root).stdout,before)
        self.assertTrue(first['observation']['cache_written'])
        sync_health.status(self.root,now=NOW+timedelta(days=1),persist=True,probe=probe)
        self.assertEqual(probe.call_count,2)

    def test_failed_probe_is_cooled_down_and_new_failure_replaces_success(self):
        probe=Mock(side_effect=[self.report(),self.report(passed=False)])
        self.status(persist=True,probe=probe)
        failed=self.status(persist=True,refresh=True,probe=probe)
        again=self.status(persist=True,probe=probe)
        self.assertEqual(probe.call_count,2)
        self.assertFalse(again['checks']['connection_verified'])
        self.assertEqual(failed['connection']['status'],'failed_or_unverified')

    def test_read_only_and_offline_never_write_cache_or_call_actions(self):
        probe=Mock(return_value=self.report())
        self.status(probe=probe)
        destination=sync_health.cache_path(self.root,fixtures.config())
        self.assertFalse(destination.exists())
        self.status(persist=True,probe=probe)
        raw=destination.read_bytes()
        data=self.status(offline=True,probe=Mock(side_effect=AssertionError('offline')))
        self.assertEqual(destination.read_bytes(),raw)
        self.assertIsNone(data['checks']['connection_verified'])
        self.assertFalse(data['observation']['connection_probe_dispatched'])

    def test_changed_mapping_invalidates_cache_and_preserves_old(self):
        probe=Mock(return_value=self.report())
        self.status(persist=True,probe=probe)
        old=sync_health.cache_path(self.root,fixtures.config()); raw=old.read_bytes()
        cfg=fixtures.config();cfg['sync']={'provider':'actions','api_version':'v2'}
        (self.root/plane_sync.CONFIG_NAME).write_text(json.dumps(cfg))
        self.status(persist=True,probe=probe)
        self.assertEqual(probe.call_count,2)
        self.assertEqual(old.read_bytes(),raw)

    def test_cache_reassesses_connection_expiring_during_cooldown(self):
        self.status(persist=True,probe=Mock(return_value=self.report(NOW-timedelta(hours=23))))
        data=sync_health.status(self.root,now=NOW+timedelta(hours=2),persist=True,
                                probe=Mock(side_effect=AssertionError('cooldown')))
        self.assertEqual(data['github_sync'],'stale')

    def test_invalid_future_and_symlink_cache_preserved(self):
        self.status(persist=True,probe=Mock(return_value=self.report()))
        destination=sync_health.cache_path(self.root,fixtures.config())
        value=json.loads(destination.read_text());value['probed_at']=(NOW+timedelta(days=1)).isoformat()
        destination.write_text(json.dumps(value)); raw=destination.read_bytes()
        with self.assertRaises(plane_sync.WorkflowError):
            self.status(persist=True,probe=Mock(side_effect=AssertionError('invalid cache')))
        self.assertEqual(destination.read_bytes(),raw)
        destination.unlink(); target=self.root/'keep';target.write_text('untouched');destination.symlink_to(target)
        with self.assertRaises(plane_sync.WorkflowError):
            self.status(persist=True)
        self.assertEqual(target.read_text(),'untouched')

    def test_secret_update_and_new_failure_are_reflected_on_refresh(self):
        first=self.report(); later=self.report(passed=False)
        later['evidence']['secret_updated_at']=(NOW+timedelta(seconds=1)).isoformat()
        probe=Mock(side_effect=[first,later])
        self.status(persist=True,probe=probe)
        data=self.status(persist=True,refresh=True,probe=probe)
        self.assertFalse(data['checks']['connection_verified'])
