"""Review regressions: preserve other sync listeners and legacy script callers."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/plane-devflow/scripts'))
import github_setup
import plane_sync
import test_github_setup as fixtures
from test_product_upgrade import release_fixture


class SyncCallerProtectionTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_legacy_caller_in_another_workflow_blocks_script_deletion(self):
        github_setup.legacy_install(self.root, apply=True)
        caller = self.write('.github/workflows/custom-check.yaml',
                            'jobs:\n  check:\n    steps:\n      - run: python3 .github/plane-devflow/plane_sync.py --help\n')
        before = {name: (self.root / name).read_bytes() for name in github_setup.bundled_files()}
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'legacy script caller'):
            github_setup.install(self.root, release=release_fixture(), upgrade=True)
        self.assertEqual({name: (self.root / name).read_bytes() for name in before}, before)
        self.assertTrue(caller.exists())

    def test_non_workflow_launcher_is_preserved_before_removing_legacy_scripts(self):
        github_setup.legacy_install(self.root, apply=True)
        self.write('scripts/sync.sh', 'cd .github/plane-devflow\npython3 action_runner.py\n')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'scripts/sync.sh'):
            github_setup.install(self.root, release=release_fixture(), upgrade=True)
        self.assertTrue((self.root / '.github/plane-devflow/action_runner.py').is_file())

    def test_an_extra_public_listener_blocks_new_setup(self):
        self.write('.github/workflows/other-sync.yml', 'steps:\n  - uses: SoaringLabs/plane-devflow@' + 'a' * 40 + '\n')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'Additional sync listener'):
            github_setup.install(self.root, release=release_fixture())
        self.assertFalse((self.root / github_setup.WORKFLOW).exists())

    def test_a_caller_added_after_planning_blocks_apply(self):
        github_setup.legacy_install(self.root, apply=True)
        release = release_fixture()
        plan = github_setup.install(self.root, release=release, upgrade=True)
        self.write('package.json', '{"scripts":{"sync":"python3 .github/plane-devflow/action_runner.py"}}')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'package.json'):
            github_setup.install(self.root, release=release, upgrade=True, apply=True,
                                 expected_files_sha256=plan['expected_files_sha256'])
        self.assertTrue((self.root / '.github/plane-devflow/action_runner.py').is_file())

    def test_an_incomplete_historical_listener_is_not_silently_duplicated(self):
        self.write('.github/workflows/old-sync.yml', 'steps:\n  - run: python3 .github/plane-for-codex/action_runner.py\n')
        with self.assertRaisesRegex(plane_sync.WorkflowError, 'old-sync.yml'):
            github_setup.install(self.root, release=release_fixture())
        self.assertFalse((self.root / github_setup.WORKFLOW).exists())

    def test_docs_mentions_and_unrelated_workflows_do_not_block_upgrade(self):
        github_setup.legacy_install(self.root, apply=True)
        self.write('README.md', 'Historical scripts live in .github/plane-devflow.')
        self.write('.agents/skills/plane-setup/scripts/installer.py', "BUNDLE = '.github/plane-devflow'\n")
        self.write('.github/workflows/test.yml', 'steps:\n  - run: python3 -m unittest\n')
        release = release_fixture()
        plan = github_setup.install(self.root, release=release, upgrade=True)
        github_setup.install(self.root, release=release, upgrade=True, apply=True,
                             expected_files_sha256=plan['expected_files_sha256'])
        self.assertFalse((self.root / '.github/plane-devflow/plane_sync.py').exists())


if __name__ == '__main__':
    unittest.main()
