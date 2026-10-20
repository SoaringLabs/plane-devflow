import contextlib
import io
import json
import sys
import unittest
from unittest.mock import patch

from test_checkout_workflow import CheckoutFixture
import checkout_workflow as checkout
import plane_workflow as workflow
import plane_sync as sync


class WriteContextTests(CheckoutFixture):
    def check(self, task="DEMO-12", paths=None, mode="write"):
        return checkout.write_context(self.root, task, mode=mode,
                                      planned_paths=paths if paths is not None else ["docs/plan.md"])

    def snapshot(self):
        return {"branch": self.git("branch", "--show-current"), "head": self.git("rev-parse", "HEAD"),
                "status": self.git("status", "--porcelain"),
                "metadata": {str(p): p.read_bytes() for p in
                             (self.root / ".git/plane-devflow").rglob("*") if p.is_file()}}

    def test_discussion_needs_no_selected_task_or_new_branch(self):
        self.git("switch", "main")
        before = self.snapshot()
        result = self.check(None, [], "discussion")
        self.assertTrue(result["ready"])
        self.assertFalse(result["repository_writes_allowed"])
        self.assertEqual(result["next_action"], "discuss_without_repository_writes")
        self.assertEqual(self.snapshot(), before)

    def test_discussion_does_not_permit_document_writes(self):
        result = self.check(mode="discussion")
        self.assertFalse(result["ready"])
        self.assertIn("discussion_does_not_allow_repository_writes", result["blockers"])

    def test_current_task_branch_is_not_task_selection(self):
        self.scope(["docs/**"])
        before = self.snapshot()
        result = self.check(None)
        self.assertFalse(result["ready"])
        self.assertIn("task_selection_required", result["blockers"])
        self.assertEqual(self.snapshot(), before)

    def test_first_plan_on_main_is_blocked_before_file_exists(self):
        self.git("switch", "main")
        before = self.snapshot()
        result = self.check()
        self.assertFalse(result["repository_writes_allowed"])
        self.assertIn("task_branch_mismatch", result["blockers"])
        self.assertEqual(result["next_action"], "prepare_selected_task_checkout")
        self.assertFalse((self.root / "docs/plan.md").exists())
        self.assertEqual(self.snapshot(), before)

    def test_new_task_cannot_write_plan_in_old_task_checkout(self):
        self.scope(["docs/**"])
        (self.root / "file.txt").write_text("old task edits")
        before = self.snapshot()
        result = self.check("DEMO-13")
        self.assertFalse(result["ready"])
        self.assertEqual(result["task"], "DEMO-13")
        self.assertEqual(result["expected_branch"], "codex/demo-13")
        self.assertEqual((self.root / "file.txt").read_text(), "old task edits")
        self.assertEqual(self.snapshot(), before)

    def test_new_task_prepares_from_base_before_scoped_document_write(self):
        self.scope()
        old_head = self.commit()
        self.assertFalse(self.check("DEMO-13")["ready"])
        prepared = workflow._prepare_checkout(self.root, "DEMO-13", apply=True)
        self.assertEqual(prepared["base_sha"], self.baseline)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.baseline)
        self.assertNotEqual(self.git("rev-parse", "HEAD"), old_head)
        stamp = checkout.context(self.root, "DEMO-13")["context_sha256"]
        checkout.context(self.root, "DEMO-13", allowed_paths=["docs/**"], expected=stamp, apply=True)
        self.assertTrue(self.check("DEMO-13")["repository_writes_allowed"])
        self.assertEqual(self.git("rev-parse", "codex/demo-12"), old_head)

    def test_planned_document_must_be_in_scope_even_before_it_exists(self):
        self.scope(["file.txt"])
        result = self.check()
        self.assertFalse(result["ready"])
        self.assertEqual(result["planned_outside_scope"], ["docs/plan.md"])
        self.assertIn("planned_writes_outside_task_scope", result["blockers"])

    def test_scoped_plan_is_allowed_without_implementation_receipt(self):
        self.scope(["docs/**"])
        before = self.snapshot()
        result = self.check(paths=["docs/research/new requirement.md"])
        self.assertTrue(result["repository_writes_allowed"], result)
        self.assertEqual(result["next_action"], "write_in_selected_task_checkout")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / ".git/plane-devflow/tasks").exists())

    def test_resume_preserves_context_and_checks_accumulated_changes(self):
        self.scope(["file.txt", "docs/**"])
        self.commit()
        self.assertTrue(self.check()["ready"])
        (self.root / "unrelated.md").write_text("keep")
        before = self.snapshot()
        self.assertIn("changes_outside_task_scope", self.check()["blockers"])
        self.assertEqual(self.snapshot(), before)

    def test_scope_and_concrete_planned_paths_are_required(self):
        self.assertIn("task_file_scope_missing", self.check()["blockers"])
        self.scope(["docs/**"])
        self.assertIn("planned_write_paths_missing", self.check(paths=[])["blockers"])

    def test_ignored_artifacts_cannot_be_adopted_by_new_task_scope(self):
        (self.root / ".git/info/exclude").write_text("docs/private.md\n")
        self.scope(["docs/**"])
        for exists in [False, True]:
            if exists:
                (self.root / "docs").mkdir()
                (self.root / "docs/private.md").write_text("old ignored report")
            before = self.snapshot()
            result = self.check(paths=["docs/private.md"])
            self.assertIn("planned_artifacts_are_git_ignored", result["blockers"])
            self.assertEqual(result["planned_ignored_paths"], ["docs/private.md"])
            self.assertEqual(result["next_action"], "choose_tracked_artifact_path_or_external_output")
            self.assertEqual(self.snapshot(), before)

    def test_already_tracked_file_is_not_blocked_by_later_ignore_rule(self):
        (self.root / ".git/info/exclude").write_text("file.txt\n")
        self.scope()
        self.assertTrue(self.check(paths=["file.txt"])["ready"])

    def test_invalid_task_cannot_inherit_current_branch(self):
        with self.assertRaises(sync.WorkflowError):
            self.check("OTHER-12")

    def test_detached_checkout_is_not_adopted(self):
        self.git("checkout", "--detach")
        before = self.snapshot()
        self.assertIn("task_branch_mismatch", self.check()["blockers"])
        self.assertEqual(self.snapshot(), before)

    def test_invalid_paths_and_symlink_escape_are_rejected(self):
        self.scope(["docs/**"])
        outside = self.directory / "outside"
        outside.mkdir()
        (self.root / "linked").symlink_to(outside, target_is_directory=True)
        (self.root / "git-link").symlink_to(self.root / ".git", target_is_directory=True)
        (self.root / "docs").mkdir()
        (self.root / "docs/file-link.md").symlink_to(self.root / "file.txt")
        (self.root / "docs/dir-link").symlink_to(self.root, target_is_directory=True)
        for path in ["../outside/plan.md", "/tmp/plan.md", ".git/config", "docs/../plan.md", "", ".",
                     "linked/plan.md", "git-link/config", "docs/file-link.md", "docs/dir-link/file.txt"]:
            with self.subTest(path=path), self.assertRaises(sync.WorkflowError):
                self.check(paths=[path])

    def test_configured_base_is_reported_without_fetching_or_switching(self):
        self.git("branch", "trunk", "main")
        self.cfg["github"]["base_branch"] = "trunk"
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        with patch.object(workflow, "run", wraps=workflow.run) as calls:
            result = self.check(None, [], "discussion")
        self.assertEqual(result["base"], "trunk")
        self.assertEqual(result["base_freshness"], "unverified")
        self.assertFalse(any(c.args[0][:2] in (["git", "fetch"], ["git", "switch"]) for c in calls.call_args_list))

    def test_cli_blocked_status_is_nonzero_and_discussion_is_success(self):
        for args, expected in [(["write-context", "DEMO-12", "--mode", "write", "--path", "docs/plan.md"], 2),
                               (["write-context", "--mode", "discussion"], 0)]:
            output = io.StringIO()
            with patch.object(sys, "argv", ["plane_workflow.py", *args, "--repo", str(self.root)]), contextlib.redirect_stdout(output):
                code = workflow.main()
            self.assertEqual(code, expected)
            self.assertEqual(json.loads(output.getvalue())["ready"], expected == 0)


if __name__ == "__main__":
    unittest.main()
