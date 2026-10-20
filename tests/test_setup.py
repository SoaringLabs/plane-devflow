"""Stage-one association invariants with isolated Git and MCP response fixtures."""
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/plane-devflow/scripts"))
import plane_sync as sync
import plane_workflow as workflow


def legacy():
    return json.loads((ROOT / "examples/plane-devflow.example.json").read_text())


def basic():
    value = legacy()
    value.update(version=2, states={}, status_sync={"enabled": False})
    return value


class BasicConfigTests(unittest.TestCase):
    def test_basic_without_targets_and_legacy_are_supported(self):
        self.assertFalse(sync.state_sync_enabled(sync.validate_config(basic())))
        self.assertTrue(sync.state_sync_enabled(sync.validate_config(legacy())))

    def test_basic_rejects_enabled_sync_or_carried_targets(self):
        for edits in ({"states": legacy()["states"]}, {"status_sync": {"enabled": True}},
                      {"status_sync": {"enabled": 0}}, {"status_sync": {"enabled": False, "token": "secret"}}):
            cfg = basic()
            cfg.update(edits)
            with self.subTest(edits=edits), self.assertRaises(sync.WorkflowError):
                sync.validate_config(cfg)

    def test_disabled_sync_keeps_state_and_upserts_comment(self):
        cfg = basic()
        item = {"id": "55555555-5555-4555-8555-555555555555", "project_id": cfg["plane"]["project_id"],
                "state_id": legacy()["states"]["in_progress"], "state": {"group": "started"}}
        class Client:
            comments = {}
            def work_item(self, task):
                return item
            def update_state(self, *args):
                raise AssertionError("Disabled sync must not write state")
            def upsert_comment(self, item, key, text):
                self.comments[key] = text
        client = Client()
        pr = {"number": 1, "html_url": "https://github.com/example/demo-project/pull/1", "title": "[DEMO-1] Task",
              "body": "", "state": "closed", "merged": True,
              "base": {"ref": "main", "repo": {"full_name": "example/demo-project"}}}
        event = {"repository": {"full_name": "example/demo-project"}, "pull_request": pr}
        for _ in range(2):
            self.assertFalse(sync.sync_event(event, cfg, client)["state_changed"])
        self.assertEqual(len(client.comments), 1)
        self.assertIn("disabled", next(iter(client.comments.values())))

    def test_pr_binding_protocol_does_not_change_with_config_version(self):
        self.assertEqual(sync.binding(basic(), "DEMO-1"), sync.binding(legacy(), "DEMO-1"))


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/example/demo-project.git")
        self.path = self.root / sync.CONFIG_NAME
        self.workspace = Path(self.temp.name) / "workspace.json"
        self.project = Path(self.temp.name) / "project.json"
        self.projects = Path(self.temp.name) / "projects.json"
        self.workspace.write_text(json.dumps({"result": {"slug": "example-workspace", "name": "Example"}}))
        self.project.write_text(json.dumps({"id": legacy()["plane"]["project_id"], "identifier": "DEMO", "name": "Demo"}))
        self.projects.write_text(json.dumps({"results": [], "next_page_results": False}))

    def git(self, *args):
        return workflow.run(["git", *args], self.root).stdout.strip()

    def args(self, **edits):
        p = legacy()["plane"]
        args = argparse.Namespace(repo=self.root, api_url=p["api_url"], app_url=p["app_url"], workspace=p["workspace"],
                                  project_id=p["project_id"], project_key="DEMO", base="main", branch_prefix=None,
                                  completion=None, in_progress=None, in_review=None, done=None, action_source=None,
                                  apply=False, replace=False, expected_config_sha256=None, disable_state_sync=False,
                                  project_file=self.project, workspace_file=self.workspace)
        for key, value in edits.items():
            setattr(args, key, value)
        return args

    def original(self, value=None):
        text = json.dumps(value or legacy(), indent=4) + "\n"
        self.path.write_text(text)
        return text

    def new_project(self):
        p = {"id": "66666666-6666-4666-8666-666666666666", "identifier": "NEW", "name": "New"}
        self.project.write_text(json.dumps(p))
        return dict(project_id=p["id"], project_key=p["identifier"], replace=True)

    def test_plan_and_cancel_leave_repository_and_auth_untouched(self):
        original = self.original()
        before = self.git("status", "--porcelain")
        with patch.object(workflow, "run", wraps=workflow.run) as commands:
            plan = workflow.configure(self.args(**self.new_project()))
        self.assertTrue(plan["project_changed"])
        self.assertEqual(self.path.read_text(), original)
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.assertFalse(any(call.args[0][0] in {"gh", "codex"} for call in commands.call_args_list))

    def test_first_setup_with_empty_project_and_no_states(self):
        args = self.args()
        plan = workflow.configure(args)
        self.assertEqual(plan["expected_config_sha256"], "missing")
        self.assertFalse(self.path.exists())
        args.apply, args.expected_config_sha256 = True, "missing"
        result = workflow.configure(args)
        self.assertEqual(sync.read_config(self.path), basic())
        self.assertTrue(result["live_selection_checked"])
        self.assertNotIn("backup", result)

    def test_same_project_preserves_legacy_preferences_and_format(self):
        cfg = legacy()
        cfg["completion"] = {"policy": "on_merge", "manual_label": "accept-me"}
        cfg["github"]["base_branch"] = "develop"
        cfg["github"]["branch_prefix"] = "tasks"
        original = self.original(cfg)
        result = workflow.configure(self.args(base=None, apply=True))
        self.assertFalse(result["changed"])
        self.assertEqual(self.path.read_text(), original)
        self.assertNotIn("backup", result)

    def test_reconfigure_backs_up_exact_bytes_and_clears_old_states(self):
        original = self.original()
        (self.root / "unrelated.txt").write_text("keep")
        args = self.args(**self.new_project())
        plan = workflow.configure(args)
        args.apply, args.expected_config_sha256 = True, plan["expected_config_sha256"]
        result = workflow.configure(args)
        self.assertEqual(Path(result["backup"]).read_text(), original)
        self.assertIn(".git", Path(result["backup"]).parts)
        self.assertEqual(sync.read_config(self.path)["states"], {})
        self.assertEqual((self.root / "unrelated.txt").read_text(), "keep")
        self.assertNotIn("backups", self.git("status", "--porcelain"))

    def test_changed_config_requires_replace_and_review_hash(self):
        original = self.original()
        changes = self.new_project()
        for edits in ({**changes, "replace": False}, {**changes, "apply": True}):
            with self.subTest(edits=edits), self.assertRaises(sync.WorkflowError):
                workflow.configure(self.args(**edits))
        self.assertEqual(self.path.read_text(), original)

    def test_concurrent_change_after_plan_is_preserved(self):
        self.original()
        args = self.args(**self.new_project())
        plan = workflow.configure(args)
        latest = legacy()
        latest["completion"]["policy"] = "on_merge"
        original = self.original(latest)
        args.apply, args.expected_config_sha256 = True, plan["expected_config_sha256"]
        with self.assertRaisesRegex(sync.WorkflowError, "changed"):
            workflow.configure(args)
        self.assertEqual(self.path.read_text(), original)

    def test_failed_atomic_replace_preserves_original(self):
        original = self.original()
        args = self.args(**self.new_project())
        args.expected_config_sha256 = workflow.configure(args)["expected_config_sha256"]
        args.apply = True
        real_replace = os.replace
        def fail_config(source, destination):
            if Path(destination).resolve() == self.path.resolve():
                raise OSError("simulated disk failure")
            return real_replace(source, destination)
        with patch.object(workflow.os, "replace", side_effect=fail_config), self.assertRaises(OSError):
            workflow.configure(args)
        self.assertEqual(self.path.read_text(), original)
        self.assertEqual(list(self.root.glob(".plane-config-*")), [])

    def test_invalid_config_can_be_diagnosed_and_repaired(self):
        self.path.write_text("broken json")
        with patch.object(workflow.shutil, "which", return_value=None):
            self.assertFalse(workflow.doctor(self.root)["config_valid"])
        args = self.args(replace=True)
        args.expected_config_sha256 = workflow.configure(args)["expected_config_sha256"]
        args.apply = True
        result = workflow.configure(args)
        self.assertEqual(Path(result["backup"]).read_text(), "broken json")
        self.assertEqual(sync.read_config(self.path), basic())

    def test_workspace_project_snapshot_mismatch_leaves_config(self):
        original = self.original()
        self.workspace.write_text(json.dumps({"slug": "another-workspace"}))
        with self.assertRaisesRegex(sync.WorkflowError, "snapshots"):
            workflow.configure(self.args())
        self.assertEqual(self.path.read_text(), original)

    def test_existing_workflow_blocks_replacement(self):
        original = self.original()
        path = self.root / ".github/workflows/plane-devflow.yml"
        path.parent.mkdir(parents=True)
        path.write_text("existing workflow")
        with self.assertRaisesRegex(sync.WorkflowError, "workflow"):
            workflow.configure(self.args(**self.new_project()))
        self.assertEqual(self.path.read_text(), original)
        self.assertEqual(path.read_text(), "existing workflow")

    def test_first_basic_mapping_does_not_break_existing_workflow(self):
        path = self.root / ".github/workflows/plane-devflow.yml"
        path.parent.mkdir(parents=True)
        path.write_text("older action")
        with self.assertRaisesRegex(sync.WorkflowError, "workflow"):
            workflow.configure(self.args(apply=True))
        self.assertFalse(self.path.exists())

    def test_cross_workspace_snapshots_are_rejected(self):
        self.workspace.write_text(json.dumps({"slug": "example-workspace", "id": "workspace-a"}))
        project = json.loads(self.project.read_text())
        project["workspace"] = "workspace-b"
        self.project.write_text(json.dumps(project))
        with self.assertRaisesRegex(sync.WorkflowError, "snapshots"):
            workflow.configure(self.args(apply=True))
        self.assertFalse(self.path.exists())

    def test_base_workflow_blocks_even_when_missing_in_checkout(self):
        self.original()
        p = self.root / ".github/workflows/plane-devflow.yml"
        p.parent.mkdir(parents=True)
        p.write_text("event workflow")
        self.git("add", ".")
        self.git("commit", "-m", "setup with workflow")
        p.unlink()
        with self.assertRaisesRegex(sync.WorkflowError, "workflow"):
            workflow.configure(self.args(**self.new_project()))

    def test_task_branch_cannot_be_retargeted(self):
        self.original()
        self.git("switch", "-c", "codex/demo-1")
        with self.assertRaisesRegex(sync.WorkflowError, "task branch"):
            workflow.configure(self.args(**self.new_project()))

    def test_basic_rejects_action_generation(self):
        with self.assertRaisesRegex(sync.WorkflowError, "deferred"):
            workflow.configure(self.args(action_source="example/plugin@" + "a" * 40, apply=True))
        self.assertFalse(self.path.exists())

    def test_symlink_mapping_is_never_replaced(self):
        other = Path(self.temp.name) / "outside.json"
        other.write_text(json.dumps(legacy()))
        self.path.symlink_to(other)
        with self.assertRaisesRegex(sync.WorkflowError, "symlink"):
            workflow.configure(self.args(replace=True))
        self.assertTrue(self.path.is_symlink())

    def test_project_recommendation_still_requires_selection(self):
        self.projects.write_text(json.dumps({"results": [
            {"id": legacy()["plane"]["project_id"], "name": "Demo project", "identifier": "DEMOPROJECT"}]}))
        result = workflow.project_options(self.root, self.projects, self.workspace)
        self.assertTrue(result["projects"][0]["recommended"])
        self.assertTrue(result["selection_required"])
        self.assertFalse(self.path.exists())

    def test_empty_project_list_offers_create_and_partial_list_rejected(self):
        result = workflow.project_options(self.root, self.projects, self.workspace)
        self.assertEqual(result["projects"], [])
        self.assertTrue(result["can_create"])
        self.projects.write_text(json.dumps({"results": [], "next_page_results": True}))
        with self.assertRaisesRegex(sync.WorkflowError, "all project pages"):
            workflow.project_options(self.root, self.projects, self.workspace)

    def test_setup_hash_lock_and_unrelated_changes_are_preserved(self):
        self.original()
        args = self.args(**self.new_project())
        args.expected_config_sha256 = workflow.configure(args)["expected_config_sha256"]
        args.apply = True
        original = self.path.read_bytes()
        with workflow.configuration_lock(self.root), self.assertRaisesRegex(sync.WorkflowError, "Another setup"):
            workflow.configure(args)
        self.assertEqual(self.path.read_bytes(), original)

    def test_basic_mapping_supports_isolated_task_branch(self):
        self.original(basic())
        (self.root / "file.txt").write_text("before")
        self.git("add", ".")
        self.git("commit", "-m", "basic setup")
        target = Path(self.temp.name) / "task"
        workflow._prepare_checkout(self.root, "DEMO-1", worktree=target, apply=True)
        self.assertEqual(sync.read_config(target / sync.CONFIG_NAME), basic())


if __name__ == "__main__":
    unittest.main()
