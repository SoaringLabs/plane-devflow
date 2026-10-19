import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/plane-for-codex/scripts"))
import checkout_workflow as checkout
import plane_workflow as workflow
import plane_sync as sync
import task_progress as receipts
from test_task_progress import ready_data, source


class CheckoutFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = (self.directory / "repo with spaces").resolve()
        self.root.mkdir()
        self.cfg = json.loads((ROOT / "examples/plane-for-codex.example.json").read_text())
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/example/demo-project.git")
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        (self.root / "file.txt").write_text("before")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.baseline = self.git("rev-parse", "HEAD")
        workflow._prepare_checkout(self.root, "DEMO-12", apply=True)

    def git(self, *args, cwd=None):
        return workflow.run(["git", *args], cwd or self.root).stdout.strip()

    def scope(self, paths=None):
        stamp = checkout.context(self.root, "DEMO-12")["context_sha256"]
        return checkout.context(self.root, "DEMO-12", allowed_paths=paths or ["file.txt"], expected=stamp, apply=True)

    def commit(self, filename="file.txt", content="after", cwd=None):
        directory = cwd or self.root
        (directory / filename).write_text(content)
        self.git("add", filename, cwd=directory)
        self.git("commit", "-m", "task change", cwd=directory)
        return self.git("rev-parse", "HEAD", cwd=directory)


class CheckoutTests(CheckoutFixture):
    def test_prepare_records_baseline_but_requires_explicit_scope(self):
        result = checkout.context(self.root, "DEMO-12")
        self.assertEqual(result["checkout"]["base_sha"], self.baseline)
        self.assertIn("task_file_scope_missing", result["blockers"])
        self.scope()
        self.assertTrue(checkout.context(self.root, "DEMO-12")["ready"])

    def test_guard_covers_committed_staged_unstaged_and_untracked_changes(self):
        self.scope()
        self.commit()
        self.assertTrue(checkout.context(self.root, "DEMO-12")["ready"])
        self.commit("unrelated.txt")
        (self.root / "staged.txt").write_text("staged")
        self.git("add", "staged.txt")
        (self.root / "unrelated.txt").write_text("unstaged")
        (self.root / "untracked.txt").write_text("untracked")
        result = checkout.context(self.root, "DEMO-12")
        self.assertEqual(result["outside_scope"], ["staged.txt", "unrelated.txt", "untracked.txt"])
        self.assertIn("changes_outside_task_scope", receipts.check_task(self.root, "DEMO-12", "implement")["blockers"])

    def test_scope_checks_both_sides_of_rename_and_paths_with_spaces(self):
        self.scope(["file.txt", "allowed/**"])
        (self.root / "allowed").mkdir()
        self.git("mv", "file.txt", "allowed/new name.txt")
        self.assertTrue(checkout.context(self.root, "DEMO-12")["ready"])
        self.scope(["allowed/**"])
        self.assertEqual(checkout.context(self.root, "DEMO-12")["outside_scope"], ["file.txt"])

    def test_branch_drift_blocks_implementation_and_draft_delivery(self):
        self.scope()
        self.git("switch", "main")
        self.assertIn("task_branch_mismatch", receipts.check_task(self.root, "DEMO-12", "implement")["blockers"])

    def test_draft_does_not_bypass_scope_check_or_push(self):
        self.scope()
        self.commit("other.txt")
        body = self.directory / "body.md"
        body.write_text(workflow.render_report(self.root, "DEMO-12", "change", "", ""))
        with patch.object(workflow, "run", wraps=workflow.run) as calls, self.assertRaisesRegex(sync.WorkflowError, "file scope"):
            workflow.delivery(self.root, "DEMO-12", "change", body, draft=True, apply=True)
        self.assertFalse(any(c.args[0][0] == "gh" or c.args[0][1] == "push" for c in calls.call_args_list))

    def test_early_integration_detected_before_resuming(self):
        self.scope()
        head = self.commit()
        self.git("update-ref", "refs/remotes/origin/main", head)
        self.assertIn("task_head_already_in_base", checkout.context(self.root, "DEMO-12")["blockers"])
        with self.assertRaisesRegex(sync.WorkflowError, "inspection"):
            workflow._prepare_checkout(self.root, "DEMO-12", apply=True)

    def test_squash_integration_detected_even_with_newer_unrelated_base_content(self):
        self.scope()
        self.commit()
        self.git("switch", "main")
        self.git("merge", "--squash", "codex/demo-12")
        self.git("commit", "-m", "squash task")
        latest = self.commit("other-task.txt")
        self.git("update-ref", "refs/remotes/origin/main", latest)
        self.git("switch", "codex/demo-12")
        self.assertIn("task_head_already_in_base", checkout.context(self.root, "DEMO-12")["blockers"])

    def test_scope_changed_during_delivery_stops_before_push(self):
        self.scope()
        head = self.commit()
        receipts.progress(self.root, "DEMO-12", update=ready_data(head), expected="missing", apply=True)
        body = self.directory / "body.md"
        body.write_text(receipts.report(self.root, "DEMO-12", "Change"))
        original = workflow.run
        writes = []
        def fake(args, cwd=None, **kwargs):
            if args[0] == "gh":
                self.scope(["file.txt", "new.txt"])
                return subprocess.CompletedProcess(args, 0, "[]", "")
            if args[:2] == ["git", "push"]:
                writes.append(args)
            return original(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fake), self.assertRaisesRegex(sync.WorkflowError, "scope changed"):
            workflow.delivery(self.root, "DEMO-12", "Change", body, apply=True)
        self.assertEqual(writes, [])

    def test_other_checkout_cannot_rebind_or_reuse_scope(self):
        self.scope()
        target = self.directory / "other checkout"
        self.git("worktree", "add", "--force", str(target), "codex/demo-12")
        self.assertIn("task_checkout_mismatch", checkout.context(target, "DEMO-12")["blockers"])
        with self.assertRaisesRegex(sync.WorkflowError, "changed"):
            checkout.context(target, "DEMO-12", allowed_paths=["file.txt"], expected="missing", apply=True)

    def test_stale_context_plan_and_invalid_scope_preserve_record(self):
        original = checkout.context(self.root, "DEMO-12")["context_sha256"]
        self.scope()
        for paths, stamp in [(["other.txt"], original), (["../outside"], checkout.context(self.root, "DEMO-12")["context_sha256"])]:
            with self.assertRaises(sync.WorkflowError):
                checkout.context(self.root, "DEMO-12", allowed_paths=paths, expected=stamp, apply=True)
        self.assertEqual(checkout.context(self.root, "DEMO-12")["checkout"]["allowed_paths"], ["file.txt"])

    def test_readonly_context_creates_no_metadata_and_history_rewrite_blocks(self):
        self.scope()
        before = sorted(p.name for p in (self.root / ".git/plane-for-codex").rglob("*"))
        checkout.context(self.root, "DEMO-12")
        self.assertEqual(sorted(p.name for p in (self.root / ".git/plane-for-codex").rglob("*")), before)
        self.git("checkout", "--orphan", "rewritten")
        self.git("commit", "--allow-empty", "-m", "different history")
        self.git("branch", "-D", "codex/demo-12")
        self.git("branch", "-m", "codex/demo-12")
        self.assertIn("task_base_history_changed", checkout.context(self.root, "DEMO-12")["blockers"])


class HandoffTests(CheckoutFixture):
    def setUp(self):
        super().setUp()
        self.scope()
        self.head = self.commit()
        self.remote = self.directory / "origin.git"
        self.git("init", "--bare", str(self.remote))
        self.git("remote", "set-url", "origin", str(self.remote))
        # Only repository identity is stubbed; fetch/switch/pull use a real local bare remote.
        self.identity_patch = patch.object(workflow, "actual_repository", return_value=self.cfg["github"]["repository"])
        self.identity_patch.start()
        self.addCleanup(self.identity_patch.stop)
        self.git("push", "origin", "main", "codex/demo-12")
        self.writer = self.directory / "writer"
        self.git("clone", "--branch", "main", str(self.remote), str(self.writer))
        self.git("config", "user.name", "Test", cwd=self.writer)
        self.git("config", "user.email", "test@example.invalid", cwd=self.writer)
        self.git("merge", "--squash", "origin/codex/demo-12", cwd=self.writer)
        self.git("commit", "-m", "squash merge", cwd=self.writer)
        self.merge = self.git("rev-parse", "HEAD", cwd=self.writer)
        self.git("push", "origin", "main", cwd=self.writer)
        data = ready_data(self.head)
        data["acceptance"] = {"head": self.head, "brief_sha256": receipts.digest(data["brief"]),
                              "evidence": "Current acceptance", "source": source(), "criteria": ["behavior"]}
        data["delivery"] = {"pr_url": "https://github.com/example/demo-project/pull/7", "plane_writeback": "confirmed",
                            "head": self.head, "evidence": "Current readback"}
        receipts.progress(self.root, "DEMO-12", update=data, expected="missing", apply=True)
        self.pr = {"url": data["delivery"]["pr_url"], "state": "MERGED", "isDraft": False, "headRefOid": self.head,
                   "baseRefName": "main", "mergeCommit": {"oid": self.merge}, "isCrossRepository": False,
                   "title": "[DEMO-12] Change", "body": "<!-- plane-for-codex " + json.dumps(sync.binding(self.cfg, "DEMO-12")) + " -->"}
        self.real_run = workflow.run
        def fake(args, cwd=None, **kwargs):
            if args[0] == "gh":
                payload = [] if args[1:3] == ["pr", "checks"] else self.pr
                return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")
            return self.real_run(args, cwd, **kwargs)
        self.run_patch = patch.object(workflow, "run", side_effect=fake)
        self.run_patch.start()
        self.addCleanup(self.run_patch.stop)

    def workitem(self):
        return {"task": "DEMO-12", "project_id": self.cfg["plane"]["project_id"], "labels": [],
                "state_group": "completed", "observed_at": datetime.now(timezone.utc).isoformat()}

    def finish(self, path=None, **kwargs):
        return checkout.finish(path or self.root, "DEMO-12", workitem=self.workitem(), **kwargs)

    def test_handoff_uses_latest_base_after_squash_and_is_idempotent(self):
        newest = self.commit("newer.txt", "another task", cwd=self.writer)
        self.git("push", "origin", "main", cwd=self.writer)
        receipt_before = receipts.progress(self.root, "DEMO-12")["record_sha256"]
        for _ in range(2):
            result = self.finish(apply=True)
            self.assertTrue(result["ready"], result)
            self.assertEqual(self.git("branch", "--show-current"), "main")
            self.assertEqual(result["head"], newest)
            self.assertEqual(result["head"], self.git("rev-parse", "origin/main"))
        self.assertEqual(receipts.progress(self.root, "DEMO-12")["record_sha256"], receipt_before)
        self.assertTrue(self.git("show-ref", "refs/heads/codex/demo-12"))

    def test_plan_is_readonly_and_not_authority_for_later_changes(self):
        before = self.git("rev-parse", "origin/main")
        self.assertTrue(self.finish()["ready"])
        self.assertEqual(self.git("rev-parse", "origin/main"), before)
        self.assertFalse((self.root / ".git/plane-for-codex/handoffs").exists())
        (self.root / "untracked.txt").write_text("preserve")
        self.assertFalse(self.finish(apply=True)["ready"])
        self.assertEqual(self.git("branch", "--show-current"), "codex/demo-12")
        self.assertEqual((self.root / "untracked.txt").read_text(), "preserve")

    def test_completion_required_and_stale_snapshot_cannot_switch(self):
        for changes in ({"state_group": "started"}, {"observed_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()}):
            item = self.workitem()
            item.update(changes)
            self.assertFalse(checkout.finish(self.root, "DEMO-12", workitem=item, apply=True)["ready"])
            self.assertEqual(self.git("branch", "--show-current"), "codex/demo-12")
        self.pr["state"] = "CLOSED"
        self.assertFalse(self.finish(apply=True)["ready"])

    def test_local_unique_or_divergent_main_is_preserved(self):
        self.git("switch", "main")
        unique = self.commit("local.txt", "preserve unique")
        self.git("switch", "codex/demo-12")
        result = self.finish(apply=True)
        self.assertFalse(result["ready"])
        self.assertEqual(self.git("rev-parse", "main"), unique)
        self.assertEqual(self.git("branch", "--show-current"), "codex/demo-12")
        self.assertIn("unique commits", result["blockers"][0])

    def test_missing_local_main_is_created_without_resetting_task(self):
        self.git("branch", "-D", "main")
        result = self.finish(apply=True)
        self.assertTrue(result["ready"], result)
        self.assertEqual(self.git("rev-parse", "main"), self.merge)
        self.assertEqual(self.git("rev-parse", "codex/demo-12"), self.head)

    def test_main_owned_by_another_worktree_is_preserved(self):
        target = self.directory / "another main"
        self.git("worktree", "add", str(target), "main")
        before = self.git("rev-parse", "HEAD", cwd=target)
        self.assertFalse(self.finish(apply=True)["ready"])
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=target), before)

    def test_task_worktree_updates_primary_and_keeps_task_checkout(self):
        self.git("switch", "main")
        target = self.directory / "task worktree"
        self.git("worktree", "add", str(target), "codex/demo-12")
        result = self.finish(path=target, apply=True)
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["path"], str(self.root))
        self.assertEqual(self.git("rev-parse", "HEAD"), self.merge)
        self.assertEqual(self.git("branch", "--show-current", cwd=target), "codex/demo-12")

    def test_dirty_primary_other_task_and_in_progress_operation_are_preserved(self):
        (self.root / "file.txt").write_text("preserve")
        self.assertFalse(self.finish(apply=True)["ready"])
        (self.root / "file.txt").write_text("after")
        self.git("switch", "--create", "codex/other-task")
        self.assertFalse(self.finish(apply=True)["ready"])
        self.git("switch", "codex/demo-12")
        (self.root / ".git/rebase-merge").mkdir()
        self.assertFalse(self.finish(apply=True)["ready"])

    def test_fetch_failure_and_pull_failure_retry_only_handoff(self):
        original = workflow.run
        for stage in ("fetch", "pull"):
            def fail(args, cwd=None, **kwargs):
                if (stage == "fetch" and args[:2] == ["git", "fetch"]) or (stage == "pull" and "pull" in args):
                    raise sync.WorkflowError("Simulated network failure")
                return original(args, cwd, **kwargs)
            with patch.object(workflow, "run", side_effect=fail):
                result = self.finish(apply=True)
            self.assertEqual(result["status"], "pending")
            self.assertEqual(result["phase"], stage)
            stamp = checkout.metadata_path(self.root, self.cfg, "DEMO-12", "handoffs")
            self.assertEqual(json.loads(stamp.read_text())["status"], "pending")
            self.assertTrue(self.finish(apply=True)["ready"])

    def test_remote_missing_merge_commit_does_not_switch(self):
        self.pr["mergeCommit"]["oid"] = "a" * 40
        self.assertFalse(self.finish(apply=True)["ready"])
        self.assertEqual(self.git("branch", "--show-current"), "codex/demo-12")

    def test_checkout_changes_during_fetch_prevent_switch_or_pull(self):
        original = workflow.run
        def fake(args, cwd=None, **kwargs):
            result = original(args, cwd, **kwargs)
            if args[:2] == ["git", "fetch"]:
                self.git("switch", "--create", "codex/another-task")
            return result
        with patch.object(workflow, "run", side_effect=fake):
            result = self.finish(apply=True)
        self.assertFalse(result["ready"])
        self.assertEqual(self.git("branch", "--show-current"), "codex/another-task")

    def test_symlink_and_lock_conflicts_preserve_metadata(self):
        checkpoint = checkout.metadata_path(self.root, self.cfg, "DEMO-12", "handoffs")
        checkpoint.parent.mkdir()
        target = self.directory / "preserved.json"
        target.write_text("preserved")
        checkpoint.symlink_to(target)
        with self.assertRaises(sync.WorkflowError):
            self.finish(apply=True)
        self.assertEqual(target.read_text(), "preserved")
        checkpoint.unlink()
        lock = checkpoint.parent.parent / "configure.lock"
        lock.write_text("busy")
        result = self.finish(apply=True)
        self.assertFalse(result["ready"])
        self.assertEqual(lock.read_text(), "busy")

    def test_other_configured_base_branch_uses_its_actual_mapping(self):
        self.git("switch", "main")
        self.cfg["github"]["base_branch"] = "trunk"
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        self.git("add", sync.CONFIG_NAME)
        self.git("commit", "-m", "map trunk")
        self.git("branch", "-m", "main", "trunk")
        # The merged base keeps the expected task binding and head; new identity gets its own receipt.
        data = ready_data(self.head)
        data["acceptance"] = {"head": self.head, "brief_sha256": receipts.digest(data["brief"]),
                              "evidence": "Current acceptance", "source": source(), "criteria": ["behavior"]}
        data["delivery"] = {"pr_url": self.pr["url"], "plane_writeback": "confirmed",
                            "head": self.head, "evidence": "Readback"}
        receipts.progress(self.root, "DEMO-12", update=data, expected="missing", apply=True)
        self.pr["baseRefName"] = "trunk"
        self.git("merge", "--squash", "codex/demo-12")
        self.git("commit", "-m", "merge task to trunk")
        self.pr["mergeCommit"]["oid"] = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "trunk")
        result = self.finish(apply=True)
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["base"], "trunk")


if __name__ == "__main__":
    unittest.main()
