"""Product identity and upgrade effects, exercised through public helper interfaces."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/plane-devflow/scripts'))
import product_release as releases
import product_upgrade as upgrades
import shared_sync
import github_setup
import plane_workflow
import plane_sync
import action_runner
import test_github_setup as fixtures


def release_fixture():
    required = ['VERSION', 'action.yml', 'plugins/plane-devflow/plugin.json',
                *[f'plugins/plane-devflow/scripts/{name}.py' for name in
                  ('plugin_version', 'plane_workflow', 'plane_sync', 'action_runner', 'product_release', 'product_upgrade', 'shared_sync')],
                *[f'skills/{name}/{file}' for name in releases.SKILLS for file in ('distribution.json', 'SKILL.md')]]
    return {'schema': 1, 'repository': releases.REPOSITORY, 'version': '0.14.0', 'tag': 'v0.14.0',
            'commit': 'a' * 40, 'channel': 'stable', 'skills': list(releases.SKILLS),
            'config_versions': [1, 2], 'binding_versions': [1], 'files': {name: 'b' * 64 for name in required}}


def command(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


class ReleaseIdentityTests(unittest.TestCase):
    def test_remote_default_discovery_is_a_read_only_git_protocol_query(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            remote, checkout = root / 'remote.git', root / 'checkout'
            remote.mkdir()
            checkout.mkdir()
            command(remote, 'init', '--bare')
            command(checkout, 'init', '-b', 'trunk')
            command(checkout, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '--allow-empty', '-m', 'Remote metadata fixture')
            command(checkout, 'remote', 'add', 'origin', str(remote))
            command(checkout, 'push', 'origin', 'trunk')
            command(remote, 'symbolic-ref', 'HEAD', 'refs/heads/trunk')
            before = command(checkout, 'for-each-ref')
            found = upgrades.remote_default(checkout)
            self.assertEqual(found, {'branch': 'trunk', 'commit': command(checkout, 'rev-parse', 'HEAD')})
            self.assertEqual(command(checkout, 'for-each-ref'), before)

    def test_resolver_peels_annotated_tags_and_rejects_manifest_commit_mismatch(self):
        manifest = release_fixture()
        release = {'draft': False, 'prerelease': False, 'tag_name': 'v0.14.0', 'target_commitish': 'main',
                   'assets': [{'name': 'plane-devflow-release.json', 'id': 1}]}
        data = [release, {'object': {'type': 'tag', 'sha': 'c' * 40}},
                {'object': {'type': 'commit', 'sha': 'a' * 40}},
                {'browser_download_url': 'https://github.com/SoaringLabs/plane-devflow/releases/download/v0.14.0/plane-devflow-release.json'}]
        with patch.object(releases, 'fetch_json', side_effect=data), patch.object(releases, 'fetch_asset', return_value=manifest):
            self.assertEqual(releases.resolve('0.14.0')['commit'], 'a' * 40)
        manifest['commit'] = 'd' * 40
        with patch.object(releases, 'fetch_json', side_effect=data), patch.object(releases, 'fetch_asset', return_value=manifest), self.assertRaisesRegex(ValueError, 'identity mismatch'):
            releases.resolve('0.14.0')

    def test_invalid_identity_and_paths_are_rejected(self):
        for field, value in [('repository', 'other/project'), ('commit', 'main'), ('tag', 'v0.13.0'),
                             ('channel', 'candidate'), ('skills', ['plane-setup']), ('config_versions', [9])]:
            data = release_fixture()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                releases.validate_manifest(data)
        for path in ['../secret', '/etc/passwd', '.git/config', 'dir\\file', 'dir//file']:
            data = release_fixture()
            data['files'][path] = '0' * 64
            with self.subTest(path=path), self.assertRaises(ValueError):
                releases.validate_manifest(data)

    def test_complete_template_and_release_are_both_required(self):
        release = release_fixture()
        files = {shared_sync.WORKFLOW: shared_sync.workflow(release['commit'], release['version']).encode()}
        self.assertEqual(shared_sync.inspect(files, fixtures.config())['status'], 'unverified')
        self.assertTrue(shared_sync.inspect(files, fixtures.config(), release)['compatible'])
        wrong = copy.deepcopy(release)
        wrong['commit'] = 'c' * 40
        self.assertFalse(shared_sync.inspect(files, fixtures.config(), wrong)['integrity_verified'])
        files[shared_sync.WORKFLOW] += b'\n# custom\n'
        self.assertIsNone(shared_sync.identity(files[shared_sync.WORKFLOW]))

    def test_public_runner_rejects_an_untrusted_commit_before_network_or_credentials(self):
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'pull_request_target', 'GITHUB_SHA': 'a' * 40,
                                     'PLANE_CONFIG_SHA': 'b' * 40}), patch.object(action_runner, 'run_action') as handler:
            self.assertEqual(action_runner.main(), 1)
            handler.assert_not_called()


class SharedInstallTests(fixtures.RepositoryTests):
    def test_shared_setup_writes_only_one_entrypoint_and_preserves_mapping(self):
        release = release_fixture()
        original = (self.root / plane_sync.CONFIG_NAME).read_bytes()
        plan = github_setup.install(self.root, release=release)
        self.assertFalse((self.root / shared_sync.WORKFLOW).exists())
        with self.assertRaises(plane_sync.WorkflowError):
            github_setup.install(self.root, release=release, apply=True)
        result = github_setup.install(self.root, release=release, apply=True, expected_files_sha256=plan['expected_files_sha256'])
        self.assertEqual(result['files'], [shared_sync.WORKFLOW])
        self.assertFalse((self.root / '.github/plane-devflow').exists())
        self.assertEqual((self.root / plane_sync.CONFIG_NAME).read_bytes(), original)

    def test_known_legacy_migrates_and_customized_code_is_preserved(self):
        github_setup.legacy_install(self.root, apply=True)
        release = release_fixture()
        plan = github_setup.install(self.root, release=release, upgrade=True)
        self.assertEqual(len(plan['changes']), 3)
        script = self.root / '.github/plane-devflow/plane_sync.py'
        script.write_text(script.read_text() + '\n# project customization\n')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'Customized'):
            github_setup.install(self.root, release=release, upgrade=True, apply=True, expected_files_sha256=plan['expected_files_sha256'])
        self.assertTrue(script.exists())

    def test_known_legacy_is_removed_in_the_same_scoped_application(self):
        github_setup.legacy_install(self.root, apply=True)
        mapping = (self.root / plane_sync.CONFIG_NAME).read_bytes()
        release = release_fixture()
        plan = github_setup.install(self.root, release=release, upgrade=True)
        result = github_setup.install(self.root, release=release, upgrade=True, apply=True,
                                      expected_files_sha256=plan['expected_files_sha256'])
        self.assertIsNotNone(shared_sync.identity((self.root / shared_sync.WORKFLOW).read_bytes()))
        self.assertFalse((self.root / '.github/plane-devflow/action_runner.py').exists())
        self.assertFalse((self.root / '.github/plane-devflow/plane_sync.py').exists())
        self.assertEqual((self.root / plane_sync.CONFIG_NAME).read_bytes(), mapping)
        self.assertTrue((Path(result['backup']) / 'snapshot.json').exists())

    def test_failed_migration_restores_original_workflow_and_scripts(self):
        github_setup.legacy_install(self.root, apply=True)
        before = {name: (self.root / name).read_bytes() for name in github_setup.bundled_files()}
        release = release_fixture()
        plan = github_setup.install(self.root, release=release, upgrade=True)
        original_unlink = Path.unlink
        failed = False
        def once(path, *args, **kwargs):
            nonlocal failed
            if path == self.root / '.github/plane-devflow/action_runner.py' and not failed:
                failed = True
                raise OSError('injected deletion failure')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', once), self.assertRaises(OSError):
            github_setup.install(self.root, release=release, upgrade=True, apply=True,
                                 expected_files_sha256=plan['expected_files_sha256'])
        self.assertEqual({name: (self.root / name).read_bytes() for name in before}, before)

    def test_target_identity_is_bound_into_the_apply_digest(self):
        release = release_fixture()
        plan = github_setup.install(self.root, release=release)
        release['commit'] = 'c' * 40
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'target changed'):
            github_setup.install(self.root, release=release, apply=True, expected_files_sha256=plan['expected_files_sha256'])

    def test_custom_workflow_is_not_overwritten_even_with_upgrade(self):
        path = self.root / shared_sync.WORKFLOW
        path.parent.mkdir(parents=True)
        path.write_text('name: user-owned workflow\n')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'Customized workflow'):
            github_setup.install(self.root, release=release_fixture(), upgrade=True)
        self.assertEqual(path.read_text(), 'name: user-owned workflow\n')

    def test_shared_remote_readiness_checks_release_instead_of_missing_legacy_scripts(self):
        release = release_fixture()
        files = {shared_sync.WORKFLOW: shared_sync.workflow(release['commit'], release['version']).encode()}
        with patch.object(releases, 'resolve', return_value=release):
            result = self.remote_check(remote_files=files)
        self.assertEqual(result['sync_bundle']['layout'], 'shared_action')
        self.assertTrue(result['checks']['sync_bundle_verified'])


class UpgradeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp = tempfile.TemporaryDirectory()
        cls.source = Path(cls.source_temp.name) / 'source'
        cls.source.mkdir()
        for name in ['VERSION', 'action.yml', 'plugins', 'skills']:
            source, target = ROOT / name, cls.source / name
            if source.is_dir():
                shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copyfile(source, target)
        command(cls.source, 'init', '-b', 'main')
        # A synthetic previous product tag lets the baseline guard distinguish
        # legitimate old payloads from a user's local modifications.
        originals = {}
        for path in cls.source.rglob('*'):
            if path.is_file() and '.git' not in path.relative_to(cls.source).parts:
                originals[path] = path.read_bytes()
        for path, content in originals.items():
            if path.name in ('VERSION', 'distribution.json', 'plugin.json', 'plugin_version.py'):
                path.write_bytes(content.replace(b'0.14.0', b'0.13.0'))
        command(cls.source, 'add', '.')
        command(cls.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Previous fixture')
        command(cls.source, 'tag', 'v0.13.0')
        for path, content in originals.items():
            path.write_bytes(content)
        command(cls.source, 'add', '.')
        command(cls.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Candidate fixture')
        cls.commit = command(cls.source, 'rev-parse', 'HEAD')
        cls.release = releases.manifest(cls.source, cls.commit)

    @classmethod
    def tearDownClass(cls):
        cls.source_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        command(self.root, 'init', '-b', 'main')
        command(self.root, 'remote', 'add', 'origin', 'https://github.com/example/demo-project.git')
        (self.root / plane_sync.CONFIG_NAME).write_text(json.dumps(fixtures.config()))
        command(self.root, 'add', '.')
        command(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Mapping')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.home = Path(self.temp.name) / 'home'
        self.home.mkdir()
        default = patch.object(upgrades, 'remote_default', side_effect=lambda _: {
            'branch': 'main', 'commit': command(self.root, 'rev-parse', 'refs/remotes/origin/main')})
        default.start()
        self.addCleanup(default.stop)

    def saved(self):
        preview = upgrades.plan(self.root, self.release, home=self.home)
        return upgrades.plan(self.root, self.release, home=self.home, expected_plan_id=preview['plan_id'], apply=True)['plan_id']

    def staged(self):
        plan_id = self.saved()
        upgrades.stage(self.root, plan_id, source=self.source, candidate_source=True, apply=True)
        return plan_id

    def no_network(self, args, *positional, **kwargs):
        if args[:2] == ['git', 'fetch']:
            return subprocess.CompletedProcess(args, 0, '', '')
        return self.real_run(args, *positional, **kwargs)

    def test_upgrade_uses_the_remote_default_instead_of_the_task_development_base(self):
        config = fixtures.config()
        config['github']['base_branch'] = 'develop'
        (self.root / plane_sync.CONFIG_NAME).write_text(json.dumps(config))
        result = upgrades.plan(self.root, self.release, home=self.home)
        self.assertEqual(result['plan']['base'], 'main')
        self.assertFalse(Path(result['record_path']).exists())

    def test_plan_is_read_only_and_mapping_change_invalidates_saved_plan(self):
        result = upgrades.plan(self.root, self.release, home=self.home)
        self.assertFalse(Path(result['record_path']).exists())
        plan_id = self.saved()
        config = fixtures.config()
        config['github']['branch_prefix'] = 'new-prefix'
        (self.root / plane_sync.CONFIG_NAME).write_text(json.dumps(config))
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'mapping changed'):
            upgrades.status(self.root, plan_id)

    def test_stage_resumes_without_changing_original_or_executing_candidate(self):
        plan_id = self.staged()
        result = upgrades.stage(self.root, plan_id, source=self.source, candidate_source=True, apply=True)
        self.assertEqual(result['status'], 'staged')
        self.assertFalse((self.root / shared_sync.WORKFLOW).exists())
        _, record = upgrades.read(self.root, plan_id)
        staged = Path(record['source'])
        (staged / 'action.yml').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'payload mismatch'):
            upgrades.stage(self.root, plan_id, source=self.source, candidate_source=True, apply=True)

    def test_project_diff_is_isolated_and_retry_does_not_allocate_another_branch(self):
        plan_id = self.staged()
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            result = upgrades.prepare_project(self.root, plan_id, apply=True)
            repeated = upgrades.prepare_project(self.root, plan_id, apply=True)
        self.assertEqual(result['project']['path'], repeated['project']['path'])
        self.assertEqual(result['status'], 'project_pr_pending')
        self.assertFalse(result['project_activated'])
        self.assertFalse((self.root / shared_sync.WORKFLOW).exists())
        self.assertEqual(command(self.root, 'branch', '--show-current'), 'main')

    def test_install_rejects_new_changes_and_never_calls_installer(self):
        plan_id = self.staged()
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            upgrades.prepare_project(self.root, plan_id, apply=True)
        path = self.root / '.agents/skills/plane-start'
        path.mkdir(parents=True)
        (path / 'custom.md').write_text('user content')
        with patch.object(upgrades, 'run_installer') as installer, self.assertRaisesRegex(plane_sync.WorkflowError, 'changed since review'):
            upgrades.install_local(self.root, plan_id, apply=True)
        installer.assert_not_called()

    def test_staged_then_deleted_unrelated_file_cannot_enter_an_upgrade_commit(self):
        plan_id = self.staged()
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            result = upgrades.prepare_project(self.root, plan_id, apply=True)
        workspace = Path(result['project']['path'])
        unrelated = workspace / 'unrelated.txt'
        unrelated.write_text('private fixture, not product scope')
        command(workspace, 'add', 'unrelated.txt')
        unrelated.unlink()
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'unrelated changes'):
            upgrades.project_pr(self.root, plan_id, apply=True)

    def test_a_recreated_legacy_script_is_preserved_before_pr_creation(self):
        github_setup.legacy_install(self.root, apply=True)
        command(self.root, 'add', '.')
        command(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Legacy layout')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        plan_id = self.staged()
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            result = upgrades.prepare_project(self.root, plan_id, apply=True)
        workspace = Path(result['project']['path'])
        recreated = workspace / '.github/plane-devflow/plane_sync.py'
        recreated.write_text('user restored this file after preparation')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'changed after preparation'):
            upgrades.project_pr(self.root, plan_id, apply=True)
        self.assertTrue(recreated.exists())

    def test_tracked_project_installation_is_staged_without_dirtying_the_original(self):
        for name in releases.SKILLS:
            subtree = 'skills/' + name
            for file in command(self.source, 'ls-tree', '-r', '--name-only', 'v0.13.0', '--', subtree).splitlines():
                target = self.root / '.agents/skills' / name / file[len(subtree) + 1:]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(releases.git(self.source, 'show', 'v0.13.0:' + file))
        command(self.root, 'add', '.')
        command(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Tracked original installation')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        plan_id = self.staged()
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            upgrades.prepare_project(self.root, plan_id, apply=True)
        def install_fixture(args, workspace):
            self.assertNotEqual(Path(workspace), self.root)
            for name in releases.SKILLS:
                shutil.rmtree(Path(workspace) / '.agents/skills' / name)
                shutil.copytree(self.source / 'skills' / name, Path(workspace) / '.agents/skills' / name)
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch.object(upgrades, 'run_installer', side_effect=install_fixture):
            result = upgrades.install_local(self.root, plan_id, apply=True)
        self.assertEqual(result['local_installation'], 'project_installation_staged')
        self.assertEqual(command(self.root, 'status', '--porcelain'), '')
        self.assertEqual(json.loads((self.root / '.agents/skills/plane-setup/distribution.json').read_text())['version'], '0.13.0')
        staged = Path(result['project']['path'])
        command(staged, 'add', '.')
        command(staged, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Upgrade project payload')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', command(staged, 'rev-parse', 'HEAD'))
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            activated = upgrades.install_local(self.root, plan_id, apply=True)
        self.assertEqual(activated['local_installation'], 'verified')
        self.assertEqual(command(self.root, 'status', '--porcelain'), '')
        self.assertEqual(json.loads((self.root / '.agents/skills/plane-setup/distribution.json').read_text())['version'], '0.14.0')

    def test_native_tracked_installation_activates_without_an_actions_workflow(self):
        config = fixtures.config()
        config['sync'] = {'provider': 'native'}
        (self.root / plane_sync.CONFIG_NAME).write_text(json.dumps(config))
        command(self.root, 'add', '.')
        command(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Native mapping')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.test_tracked_project_installation_is_staged_without_dirtying_the_original()
        self.assertFalse((self.root / shared_sync.WORKFLOW).exists())

    def test_release_source_drift_is_detected_without_installing(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / 'copy'
            shutil.copytree(self.source, copied)
            (copied / 'plugins/plane-devflow/scripts/action_runner.py').write_text('unexpected code')
            with self.assertRaisesRegex(ValueError, 'payload mismatch'):
                releases.verify_source(copied, self.release)

    def test_green_connection_does_not_verify_an_unrecognized_action_identity(self):
        plan_id = self.staged()
        current = command(self.root, 'rev-parse', 'HEAD')
        report = {'configuration_status': 'complete', 'checks': {'connection_verified': True},
                  'sync_bundle': {'installed_version': self.release['version'], 'source_commit': self.release['commit'],
                                  'integrity_verified': None, 'compatible': None},
                  'evidence': {'default_sha': current}}
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network), patch.object(github_setup, 'check', return_value=report):
            result = upgrades.verify_project(self.root, plan_id)
        self.assertFalse(result['connection_verified'])
        self.assertNotEqual(result['status'], 'complete')

    def test_saved_source_does_not_allow_an_extra_executable_module(self):
        plan_id = self.staged()
        _, record = upgrades.read(self.root, plan_id)
        (Path(record['source']) / 'plugins/plane-devflow/scripts/unreviewed.py').write_text('raise RuntimeError()')
        with self.assertRaisesRegex(ValueError, 'Unexpected or missing'):
            upgrades.prepare_project(self.root, plan_id, apply=True)

    def test_reverse_diff_restores_legacy_bytes_without_reverting_the_default_branch(self):
        github_setup.legacy_install(self.root, apply=True)
        original = {name: (self.root / name).read_bytes() for name in github_setup.bundled_files()}
        command(self.root, 'add', '.')
        command(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Historical deployment')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        plan_id = self.staged()
        self.real_run = plane_workflow.run
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            prepared = upgrades.prepare_project(self.root, plan_id, apply=True)
        workspace = Path(prepared['project']['path'])
        command(workspace, 'add', '.')
        command(workspace, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Migrated fixture')
        deployed = command(workspace, 'rev-parse', 'HEAD')
        command(self.root, 'update-ref', 'refs/remotes/origin/main', deployed)
        with patch.object(plane_workflow, 'run', side_effect=self.no_network):
            result = upgrades.rollback(self.root, plan_id, apply=True)
        reverse = Path(result['workspace'])
        self.assertEqual({name: (reverse / name).read_bytes() for name in original}, original)
        self.assertEqual(command(self.root, 'rev-parse', 'refs/remotes/origin/main'), deployed)
        self.assertEqual(command(self.root, 'branch', '--show-current'), 'main')


if __name__ == '__main__':
    unittest.main()
