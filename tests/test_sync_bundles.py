"""Independent release identities and daily, read-only bundle maintenance checks."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/plane-devflow/scripts'))
import sync_bundle as bundles
import github_setup
import onboarding
import test_github_setup as fixtures


def old_bundle():
    files = bundles.bundled_files()
    key = bundles.BUNDLE + '/plane_sync.py'
    files[key] = files[key].replace(b'VERSION = "0.10.1"', b'VERSION = "0.10.0"')
    return files


class BundleIdentityTests(unittest.TestCase):
    def test_current_exact_bundle_is_verified_and_has_no_update(self):
        bundles.verify_current_bundle()
        result = bundles.inspect_bundle(bundles.bundled_files(), fixtures.config())
        self.assertEqual(result['status'], 'current')
        self.assertTrue(result['integrity_verified'])
        self.assertTrue(result['compatible'])
        self.assertFalse(result['update_available'])
        self.assertFalse(result['upgrade_required'])
        self.assertEqual(result['catalog_source'], 'installed_plugin')

    def test_modified_script_or_workflow_is_not_trusted_by_its_version(self):
        for name in bundles.bundled_files():
            with self.subTest(name=name):
                files = bundles.bundled_files()
                files[name] += b'\n# custom content still claims the same version\n'
                result = bundles.inspect_bundle(files, fixtures.config())
                self.assertEqual(result['status'], 'unrecognized')
                self.assertFalse(result['integrity_verified'])
                self.assertFalse(result['compatible'])
                self.assertIsNone(result['installed_version'])
                self.assertIsNone(result['update_available'])

    def test_incomplete_read_has_unknown_compatibility(self):
        files = bundles.bundled_files()
        files[bundles.WORKFLOW] = None
        result = bundles.inspect_bundle(files, fixtures.config())
        self.assertEqual(result['status'], 'unverified')
        for field in ['integrity_verified', 'compatible', 'update_available', 'upgrade_required']:
            self.assertIsNone(result[field])

    def test_support_config_and_binding_restrictions_require_review(self):
        for changes in [{'support': 'upgrade_required'}, {'config_versions': [2]}, {'binding_versions': [2]}]:
            with self.subTest(changes=changes):
                releases = copy.deepcopy(bundles.RELEASES)
                releases['0.10.0'].update(changes)
                with patch.object(bundles, 'RELEASES', releases):
                    result = bundles.inspect_bundle(old_bundle(), fixtures.config())
                self.assertTrue(result['integrity_verified'])
                self.assertFalse(result['compatible'])
                self.assertTrue(result['upgrade_required'])
                self.assertEqual(result['status'], 'upgrade_required')

    def test_invalid_or_ambiguous_catalog_is_rejected(self):
        for change in ['digest', 'missing_file', 'duplicate', 'support']:
            with self.subTest(change=change):
                releases = copy.deepcopy(bundles.RELEASES)
                if change == 'digest':
                    releases['0.10.0']['files'][bundles.WORKFLOW] = 'invalid'
                elif change == 'missing_file':
                    del releases['0.10.0']['files'][bundles.WORKFLOW]
                elif change == 'duplicate':
                    releases['0.10.0']['files'] = releases['0.10.1']['files']
                else:
                    releases['0.10.1']['support'] = 'upgrade_required'
                with patch.object(bundles, 'RELEASES', releases), self.assertRaises(ValueError):
                    bundles.inspect_bundle(old_bundle(), fixtures.config())


class DailyBundleTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp
    remote_check = fixtures.RepositoryTests.remote_check

    def daily(self, files):
        github_setup.legacy_install(self.root, apply=True)
        for name, data in files.items():
            (self.root / name).write_bytes(data)
        task = self.root / '.git/plane-devflow/tasks/in-flight.json'
        task.parent.mkdir(parents=True)
        task.write_text('{"preserve":"in-flight task"}\n')
        protected = [self.root / '.plane-devflow.json', task, *[self.root / name for name in files]]
        before = {path: path.read_bytes() for path in protected}
        with patch.object(onboarding.shutil, 'which', return_value='/test/gh'), \
             patch.object(onboarding, 'check', side_effect=lambda _: self.remote_check(remote_files=files)):
            result = onboarding.progress(self.root)
        self.assertFalse(result['checkpoint_written'])
        self.assertFalse(Path(result['checkpoint_path']).exists())
        self.assertEqual({path: path.read_bytes() for path in protected}, before)
        self.assertNotIn('credential_guide', result)
        return result

    def test_optional_update_does_not_interrupt_daily_task_or_replace_files(self):
        result = self.daily(old_bundle())
        self.assertEqual(result['readiness']['github_sync'], 'ready')
        self.assertEqual(result['next_step'], 'connection_verified')
        self.assertEqual(result['sync_bundle']['status'], 'update_available')
        self.assertIn('可继续当前任务', result['maintenance_notice'])
        self.assertTrue(result['readiness']['local_files_prepared'])

    def test_required_upgrade_is_separate_from_credentials_or_task_work(self):
        releases = copy.deepcopy(bundles.RELEASES)
        releases['0.10.0']['support'] = 'upgrade_required'
        with patch.object(bundles, 'RELEASES', releases):
            result = self.daily(old_bundle())
        self.assertEqual(result['readiness']['github_sync'], 'not_ready')
        self.assertEqual(result['next_step'], 'review_sync_bundle_upgrade')
        self.assertTrue(result['sync_bundle']['upgrade_required'])

    def test_unknown_modified_bundle_is_preserved_for_review(self):
        files = bundles.bundled_files()
        files[bundles.WORKFLOW] += b'\n# intentional user customization\n'
        result = self.daily(files)
        self.assertEqual(result['readiness']['github_sync'], 'not_ready')
        self.assertEqual(result['next_step'], 'review_sync_bundle_files')
        self.assertEqual(result['sync_bundle']['status'], 'unrecognized')

    def test_legacy_checkpoint_is_read_but_never_reused_as_current_proof(self):
        from datetime import datetime, timezone
        config = fixtures.config()
        checkpoint = onboarding.checkpoint_path(self.root, config)
        checkpoint.parent.mkdir(parents=True)
        legacy = {'version': 1, 'config_sha256': github_setup.config_digest(config),
                  'reported_step': 'secret-saved', 'observed_at': datetime.now(timezone.utc).isoformat(),
                  'remote_checks': {'remote_files_match': True, 'connection_verified': True}}
        checkpoint.write_text(json.dumps(legacy));before = checkpoint.read_bytes()
        report = github_setup.assess(config)
        with patch.object(onboarding.shutil, 'which', return_value='/test/gh'), \
             patch.object(onboarding, 'check', return_value=report):
            result = onboarding.progress(self.root)
        self.assertEqual(result['recovery'], 'resumed')
        self.assertEqual(result['readiness']['initialization'], 'partial')
        self.assertFalse(result['cached_checks_reused_as_proof'])
        self.assertEqual(checkpoint.read_bytes(), before)

    def test_saved_checkpoint_keeps_legacy_schema_for_other_plugin_sessions(self):
        report = self.remote_check(remote_files=old_bundle())
        with patch.object(onboarding.shutil, 'which', return_value='/test/gh'), \
             patch.object(onboarding, 'check', return_value=report):
            result = onboarding.progress(self.root, apply=True)
        payload = json.loads(Path(result['checkpoint_path']).read_text())
        legacy_keys = {'actions_enabled', 'workflow_active', 'remote_files_match',
                       'remote_config_matches', 'secret_present', 'connection_verified'}
        self.assertEqual(set(payload['remote_checks']), legacy_keys)
        self.assertFalse(payload['remote_checks']['remote_files_match'])
        self.assertEqual(result['readiness']['github_sync'], 'ready')
        self.assertTrue(result['readiness']['checks']['sync_bundle_verified'])
