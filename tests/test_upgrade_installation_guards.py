"""Protect host copies and unrelated Skills CLI metadata during scoped upgrades."""
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
import product_upgrade as upgrades
from plane_sync import WorkflowError


class InstallationGuardsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'project'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-b', 'main'], cwd=self.root, check=True, capture_output=True)
        self.canonical = self.root / '.agents/skills'
        for name in upgrades.SKILLS:
            skill = self.canonical / name
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('Original fixture')
            (skill / 'distribution.json').write_text(json.dumps({
                'generator': 'plane-devflow/build_skills.py', 'skill': name, 'version': '0.13.0'}))
        self.host = self.root / '.claude/skills/plane-start'

    def selected(self):
        return upgrades.installation(self.root, 'project', 'claude-code')

    def test_custom_host_copy_is_rejected_even_with_a_valid_canonical_installation(self):
        shutil.copytree(self.canonical / 'plane-start', self.host)
        sentinel = self.host / 'private-custom.txt'
        sentinel.write_text('Preserve this')
        with self.assertRaisesRegex(WorkflowError, 'Host-specific skill files'):
            self.selected()
        self.assertEqual(sentinel.read_text(), 'Preserve this')

    def test_normal_host_copies_and_canonical_links_are_recognized(self):
        shutil.copytree(self.canonical / 'plane-start', self.host)
        selected = self.selected()
        self.assertEqual(selected['host_entries']['.claude/skills/plane-start']['kind'], 'copy')
        shutil.rmtree(self.host)
        self.host.symlink_to('../../../.agents/skills/plane-start', target_is_directory=True)
        # This relative path is intentionally broken: do not follow or replace it.
        with self.assertRaisesRegex(WorkflowError, 'redirects'):
            self.selected()
        self.host.unlink()
        self.host.symlink_to(self.canonical / 'plane-start', target_is_directory=True)
        self.assertEqual(self.selected()['host_entries']['.claude/skills/plane-start']['kind'], 'canonical_link')

    def test_host_parent_redirect_is_rejected_without_reading_the_other_scope(self):
        outside = Path(self.temporary.name) / 'other-scope'
        outside.mkdir()
        (self.root / '.claude').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(WorkflowError, 'parents must not be symlinks'):
            self.selected()
        self.assertFalse((outside / 'skills').exists())

    def test_host_drift_after_planning_blocks_installer_before_mutation(self):
        selected = self.selected()
        self.host.mkdir(parents=True)
        sentinel = self.host / 'private-custom.txt'
        sentinel.write_text('New work')
        source = Path(self.temporary.name) / 'staged-source'
        shutil.copytree(self.canonical, source / 'skills')
        record = {'plan': {'installation': selected, 'channel': 'skills', 'target': {}},
                  'source': str(source), 'project': {'status': 'diff_prepared'}, 'local': 'pending'}
        with patch.object(upgrades, 'read', return_value=(self.root, record)), \
                patch.object(upgrades, 'verify_source'), patch.object(upgrades, 'run_installer') as installer:
            with self.assertRaisesRegex(WorkflowError, 'Host skill files changed'):
                upgrades._install_local(self.root, 'unused', apply=True)
        installer.assert_not_called()
        self.assertEqual(sentinel.read_text(), 'New work')

    def test_selected_host_copy_refresh_does_not_authorize_another_host_change(self):
        selected = self.selected()
        expected = {name: upgrades.inventory(self.canonical / name) for name in upgrades.SKILLS}
        shutil.copytree(self.canonical / 'plane-start', self.host)
        upgrades.verify_host_entries(selected, self.root, self.canonical, expected, resumed=True)
        other = self.root / '.cursor/skills/plane-start'
        shutil.copytree(self.canonical / 'plane-start', other)
        with self.assertRaisesRegex(WorkflowError, 'Host skill files changed'):
            upgrades.verify_host_entries(selected, self.root, self.canonical, expected, resumed=True)

    def test_only_product_lock_entries_may_change_in_upgrade_pr(self):
        original = {'version': 1, 'metadata': {'keep': 'yes'}, 'skills': {
            'other-skill': {'source': 'owner/other', 'sourceType': 'github'},
            'plane-start': {'source': 'old/product'}}}
        path = self.root / 'skills-lock.json'
        path.write_text(json.dumps(original))
        selected = self.selected()
        changed = copy.deepcopy(original)
        changed['skills']['plane-start'] = {'source': 'new/product'}
        path.write_text(json.dumps(changed))
        upgrades.verify_project_lock(selected, self.root, allow_product_changes=True)
        changed['skills']['other-skill']['source'] = 'unrelated/new-source'
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(WorkflowError, 'unrelated changes'):
            upgrades.verify_project_lock(selected, self.root, allow_product_changes=True)
        changed = copy.deepcopy(original)
        changed.pop('metadata')
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(WorkflowError, 'unrelated changes'):
            upgrades.verify_project_lock(selected, self.root, allow_product_changes=True)

    def test_upgrade_pr_rejects_unrelated_lock_entry_before_gh_or_push(self):
        original = {'version': 1, 'skills': {'other-skill': {'source': 'keep/original'}}}
        lock = self.root / 'skills-lock.json'
        lock.write_text(json.dumps(original))
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True, capture_output=True)
        subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-m', 'Original installation'], cwd=self.root, check=True, capture_output=True)
        base = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()
        selected = self.selected()
        target = {'version': '0.14.0', 'commit': 'a' * 40, 'files': {
            'skills/' + name + '/' + file: value
            for name in upgrades.SKILLS for file, value in upgrades.inventory(self.canonical / name).items()}}
        record = {'plan': {'installation': selected, 'channel': 'skills', 'target': target, 'base_sha': base,
                           'base': 'main', 'project_plan': {'provider': 'native', 'changes': {}}},
                  'project': {'status': 'diff_prepared', 'branch': 'main', 'path': str(self.root)},
                  'local': 'project_installation_staged'}
        lock.write_text(json.dumps({'version': 1, 'skills': {'other-skill': {'source': 'unrelated/changed'}}}))
        from plane_workflow import run as real_run
        commands = []
        def guarded_run(args, *positional, **kwargs):
            commands.append(args)
            return real_run(args, *positional, **kwargs)
        with patch.object(upgrades, 'read', return_value=(self.root, record)), \
                patch('plane_workflow.run', side_effect=guarded_run):
            with self.assertRaisesRegex(WorkflowError, 'unrelated changes'):
                upgrades.project_pr(self.root, 'a' * 64, apply=True)
        self.assertFalse(any(args[0] == 'gh' or args[:2] == ['git', 'push'] for args in commands))

    def test_cli_rewrite_retains_unknown_metadata_and_unrelated_lock_entries(self):
        original = {'version': 1, 'extra': {'keep': 1}, 'skills': {
            'other-skill': {'source': '../other', 'sourceType': 'local'},
            'plane-start': {'source': 'old/product'}}}
        path = self.root / 'skills-lock.json'
        path.write_text(json.dumps(original))
        selected = self.selected()
        path.write_text(json.dumps({'version': 1, 'skills': {
            'other-skill': {'source': './normalized-other', 'sourceType': 'local'},
            'plane-start': {'source': 'new/product'}}}))
        upgrades.preserve_lock_metadata(selected, self.root)
        actual = json.loads(path.read_text())
        self.assertEqual(actual['extra'], original['extra'])
        self.assertEqual(actual['skills']['other-skill'], original['skills']['other-skill'])
        self.assertEqual(actual['skills']['plane-start']['source'], 'new/product')
        upgrades.verify_project_lock(selected, self.root, allow_product_changes=True)

    def test_malformed_or_redirected_lock_is_preserved(self):
        path = self.root / 'skills-lock.json'
        path.write_text('{broken')
        with self.assertRaisesRegex(ValueError, 'Cannot read'):
            self.selected()
        self.assertEqual(path.read_text(), '{broken')
        path.unlink()
        target = Path(self.temporary.name) / 'outside-lock'
        target.write_text('private')
        path.symlink_to(target)
        with self.assertRaisesRegex(WorkflowError, 'must not be a symlink'):
            self.selected()
        self.assertEqual(target.read_text(), 'private')

    def test_global_metadata_lock_preserves_unrelated_entries_at_xdg_location(self):
        home = Path(self.temporary.name) / 'global-home'
        state = home / '.state'
        lock = state / 'skills/.skill-lock.json'
        lock.parent.mkdir(parents=True)
        original = {'version': 3, 'extra': 'retain', 'skills': {'other-skill': {'source': 'owner/other'}}}
        lock.write_text(json.dumps(original))
        with patch.dict(os.environ, {'XDG_STATE_HOME': str(state)}):
            selected = upgrades.installation(self.root, 'global', 'codex', home=home)
        changed = copy.deepcopy(original)
        changed['skills']['plane-start'] = {'source': 'new/product'}
        lock.write_text(json.dumps(changed))
        upgrades.verify_global_lock(selected, allow_product_changes=True)
        changed['skills']['other-skill']['source'] = 'unrelated/change'
        lock.write_text(json.dumps(changed))
        with self.assertRaisesRegex(WorkflowError, 'Global skills lock changed'):
            upgrades.verify_global_lock(selected, allow_product_changes=True)

    def test_initial_global_lock_accepts_only_empty_default_prompt_state(self):
        self.assertTrue(upgrades.lock_changes_are_scoped(None, {
            'version': 3, 'skills': {'plane-start': {'source': 'product'}}, 'dismissed': {}}, 3))
        self.assertFalse(upgrades.lock_changes_are_scoped(None, {
            'version': 3, 'skills': {'other-skill': {'source': 'unrelated'}}, 'dismissed': {}}, 3))
        self.assertFalse(upgrades.lock_changes_are_scoped(None, {
            'version': 3, 'skills': {}, 'dismissed': {'other-prompt': True}}, 3))
        self.assertFalse(upgrades.lock_changes_are_scoped(None, {
            'version': 3, 'skills': {}, 'dismissed': {}, 'unknown': 1}, 3))

    def test_global_environment_drift_stops_before_installer_and_preserves_other_scope(self):
        home = (Path(self.temporary.name) / 'global-home').resolve()
        home.mkdir()
        alternate = (Path(self.temporary.name) / 'other-home').resolve()
        alternate.mkdir()
        sentinel = alternate / 'private-scope.txt'
        sentinel.write_text('Preserve unrelated scope')
        original_env = {'HOME': str(home), 'USERPROFILE': str(home),
                        'XDG_STATE_HOME': str(home / '.local/state'), 'CLAUDE_CONFIG_DIR': str(home / '.claude')}
        with patch.dict(os.environ, original_env):
            selected = upgrades.installation(self.root, 'global', 'claude-code')
        record = {'plan': {'installation': selected, 'channel': 'skills', 'target': {}},
                  'source': '/unused-staged-source', 'project': {'status': 'native'}, 'local': 'pending'}
        for changes in ({'HOME': str(alternate), 'USERPROFILE': str(alternate)},
                        {'XDG_STATE_HOME': str(alternate / 'state')},
                        {'CLAUDE_CONFIG_DIR': str(alternate / 'claude')}):
            with self.subTest(changes=changes), patch.dict(os.environ, dict(original_env, **changes)), \
                    patch.object(upgrades, 'read', return_value=(self.root, record)), \
                    patch.object(upgrades, 'verify_source') as source_check, \
                    patch.object(upgrades, 'run_installer') as installer:
                with self.assertRaisesRegex(WorkflowError, 'changed since review'):
                    upgrades._install_local(self.root, 'unused', apply=True)
                installer.assert_not_called()
                source_check.assert_not_called()
                self.assertEqual(sentinel.read_text(), 'Preserve unrelated scope')
                self.assertEqual(list(alternate.iterdir()), [sentinel])

    def test_project_claude_target_uses_cwd_despite_global_config_override(self):
        # Confirmed against the pinned CLI getAgentBaseDir: globalSkillsDir is
        # consulted only with --global; project installs always use cwd/.claude.
        with patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': '/unused-other-global-scope'}):
            upgrades.verify_installer_environment({'scope': 'project', 'host': 'claude-code'})

    def test_status_detects_tampered_active_host_copy(self):
        for name in upgrades.SKILLS:
            shutil.copytree(self.canonical / name, self.root / '.claude/skills' / name)
        selected = self.selected()
        (self.host / 'SKILL.md').write_text('Tampered after verification')
        target = {'version': '0.14.0', 'commit': 'a' * 40, 'files': {
            'skills/' + name + '/' + file: value
            for name in upgrades.SKILLS for file, value in upgrades.inventory(self.canonical / name).items()}}
        record = {'plan': {'installation': selected, 'channel': 'skills', 'target': target,
                           'base': 'main', 'project_plan': {'provider': 'native'}},
                  'source': '/unused-staged-source', 'project': {'status': 'native'}, 'local': 'verified',
                  'verification': None}
        with patch.object(upgrades, 'read', return_value=(self.root, record)), \
                patch.object(upgrades, 'tracked_payload_deployed', return_value=True):
            result = upgrades.status(self.root, 'a' * 64)
        self.assertEqual(result['local_installation'], 'changed_after_verification')


if __name__ == '__main__':
    unittest.main()
