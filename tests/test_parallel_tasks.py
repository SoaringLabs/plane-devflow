"""Real Git worktrees and origin; GitHub is a contract fixture, never a live write."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/plane-devflow/scripts"))
import checkout_workflow as checkout
import plane_workflow as workflow
import task_progress as receipts
import task_workspaces as workspaces
import plane_sync as sync
from test_task_progress import ready_data, source


class ParallelFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.root = self.directory / "project with spaces"
        self.root.mkdir()
        self.cfg = json.loads((ROOT / "examples/plane-devflow.example.json").read_text())
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        (self.root / "shared.txt").write_text("original\n")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        self.baseline = self.git("rev-parse", "HEAD")
        self.remote = self.directory / "origin.git"
        self.git("init", "--bare", str(self.remote))
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "origin", "main")
        # Only identity is synthetic. Fetch/push/merge/worktree use the real bare origin.
        p = patch.object(workflow, "actual_repository", return_value=self.cfg["github"]["repository"])
        p.start()
        self.addCleanup(p.stop)
        self.writer = self.directory / "main writer"
        self.git("clone", "--branch", "main", str(self.remote), str(self.writer))
        self.git("config", "user.name", "Fixture", cwd=self.writer)
        self.git("config", "user.email", "fixture@example.invalid", cwd=self.writer)

    def git(self, *args, cwd=None):
        return workflow.run(["git", *args], cwd or self.root).stdout.strip()

    def start(self, task, paths=None, caller=None):
        prepared = workflow.prepare(caller or self.root, task, apply=True)
        target = Path(prepared["path"])
        c = checkout.context(target, task)
        if "task_file_scope_missing" in c["blockers"]:
            checkout.context(target, task, allowed_paths=paths or ["shared.txt"],
                             expected=c["context_sha256"], apply=True)
        return target

    def commit(self, target, name, content):
        (target / name).write_text(content)
        self.git("add", name, cwd=target)
        self.git("commit", "-m", "task change", cwd=target)
        return self.git("rev-parse", "HEAD", cwd=target)

    def merge_to_origin(self, task):
        self.git("fetch", "origin", cwd=self.writer)
        self.git("merge", "--squash", "origin/codex/" + task.lower(), cwd=self.writer)
        self.git("commit", "-m", "accepted PR " + task, cwd=self.writer)
        self.git("push", "origin", "main", cwd=self.writer)
        return self.git("rev-parse", "HEAD", cwd=self.writer)


class ParallelTaskTests(ParallelFixture):
    def test_default_plan_is_readonly_and_apply_never_switches_primary(self):
        plan = workflow.prepare(self.root, "DEMO-12")
        self.assertTrue(plan["isolated"])
        self.assertFalse(Path(plan["path"]).exists())
        self.assertFalse((self.root / ".git/plane-devflow").exists())
        (self.root / "shared.txt").write_text("primary user edits")
        target = self.start("DEMO-12")
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.baseline)
        self.assertEqual((self.root / "shared.txt").read_text(), "primary user edits")
        self.assertEqual((target / "shared.txt").read_text(), "original\n")
        self.assertFalse(target.is_relative_to(self.root))

    def test_two_chat_callers_get_distinct_main_based_branches(self):
        a = self.start("DEMO-12")
        a_head = self.commit(a, "shared.txt", "A changes\n")
        b = self.start("DEMO-13", caller=a)
        self.assertNotEqual(a, b)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=b), self.baseline)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=a), a_head)
        self.assertEqual(self.git("branch", "--show-current", cwd=a), "codex/demo-12")
        self.assertEqual(self.git("branch", "--show-current", cwd=b), "codex/demo-13")
        (b / "shared.txt").write_text("B uncommitted\n")
        self.assertEqual((a / "shared.txt").read_text(), "A changes\n")
        c = self.start("DEMO-14", caller=b)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=c), self.baseline)
        self.assertEqual((b / "shared.txt").read_text(), "B uncommitted\n")
        self.assertFalse(checkout.context(self.root, "DEMO-13")["ready"])
        self.assertTrue(checkout.write_context(b, "DEMO-13", mode="write", planned_paths=["shared.txt"])["ready"])

    def test_simultaneous_preparation_is_serialized_without_stealing_workspaces(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda task: workflow.prepare(self.root, task, apply=True), ["DEMO-12", "DEMO-13"]))
        self.assertEqual(len({r["path"] for r in results}), 2)
        self.assertTrue(all(r["base_sha"] == self.baseline for r in results))
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_new_chat_resumes_original_path_and_never_rebinds(self):
        a = self.start("DEMO-12")
        head = self.commit(a, "shared.txt", "A\n")
        c = checkout.context(a, "DEMO-12")
        resumed = workflow.prepare(self.root, "DEMO-12", apply=True)
        self.assertEqual(Path(resumed["execution_path"]), a)
        self.assertEqual(resumed["operation"], "resume")
        self.assertEqual(checkout.context(a, "DEMO-12")["context_sha256"], c["context_sha256"])
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=a), head)
        with self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-12", worktree=self.directory / "replacement", apply=True)

    def test_fetch_failure_creates_no_branch_or_workspace(self):
        original = workflow.run
        def fail(args, cwd=None, **kwargs):
            if args[:2] == ["git", "fetch"]:
                raise sync.WorkflowError("fixture fetch failure")
            return original(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fail), self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-12", apply=True)
        self.assertEqual(self.git("branch", "--list", "codex/demo-12"), "")
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_codex_style_detached_worktree_is_named_without_creating_another(self):
        managed = self.directory / "managed worktree"
        self.git("worktree", "add", "--detach", str(managed), "origin/main")
        result = workflow.prepare(managed, "DEMO-12", in_place=True, apply=True)
        self.assertEqual(Path(result["execution_path"]), managed)
        self.assertEqual(self.git("branch", "--show-current", cwd=managed), "codex/demo-12")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=managed), self.baseline)
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_detached_unique_work_is_preserved(self):
        managed = self.directory / "managed worktree"
        self.git("worktree", "add", "--detach", str(managed), "origin/main")
        head = self.commit(managed, "unique.txt", "preserve detached work")
        with self.assertRaisesRegex(sync.WorkflowError, "unique commits"):
            workflow.prepare(managed, "DEMO-12", in_place=True, apply=True)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=managed), head)
        self.assertEqual(self.git("branch", "--show-current", cwd=managed), "")

    def test_simultaneous_managed_worktrees_share_preparation_lock(self):
        targets = [self.directory / name for name in ("managed A", "managed B")]
        for target in targets:
            self.git("worktree", "add", "--detach", str(target), "origin/main")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda item: workflow.prepare(item[0], item[1], in_place=True, apply=True),
                                    zip(targets, ["DEMO-12", "DEMO-13"])))
        self.assertEqual([r["branch"] for r in results], ["codex/demo-12", "codex/demo-13"])
        self.assertTrue(all(r["base_sha"] == self.baseline for r in results))
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_new_task_fetches_main_after_another_pr_merged(self):
        self.commit(self.writer, "new-main.txt", "new base\n")
        newest = self.git("rev-parse", "HEAD", cwd=self.writer)
        self.git("push", "origin", "main", cwd=self.writer)
        b = self.start("DEMO-13", ["shared.txt"])
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=b), newest)
        self.assertEqual(checkout.context(b, "DEMO-13")["checkout"]["base_sha"], newest)
        self.assertEqual(self.git("rev-parse", "main"), self.baseline)

    def test_clean_base_merge_excludes_other_task_files_but_preserves_scope(self):
        a = self.start("DEMO-12", ["a.txt"])
        b = self.start("DEMO-13", ["b.txt"])
        self.commit(a, "a.txt", "A\n")
        b_head = self.commit(b, "b.txt", "B\n")
        self.git("push", "origin", "codex/demo-12", cwd=a)
        self.merge_to_origin("DEMO-12")
        receipt = ready_data(b_head)
        receipts.progress(b, "DEMO-13", update=receipt, expected="missing", apply=True)
        before = checkout.context(b, "DEMO-13")["checkout"]
        result = workspaces.sync_task(b, "DEMO-13", apply=True)
        self.assertTrue(result["ready"], result)
        self.assertTrue(result["needs_reverification"])
        after = checkout.context(b, "DEMO-13")
        self.assertEqual(after["checkout"], before)
        self.assertEqual(after["changed_paths"], ["b.txt"])
        self.assertTrue((b / "a.txt").exists())
        stale = receipts.check_task(b, "DEMO-13", "review")
        self.assertIn("self_review_missing_or_stale", stale["blockers"])
        self.assertIn("criterion_unverified:behavior", stale["blockers"])
        self.assertTrue(workspaces.sync_task(b, "DEMO-13", apply=True)["ready"])
        (b / "a.txt").write_text("B tries to edit A file")
        self.assertIn("changes_outside_task_scope", checkout.context(b, "DEMO-13")["blockers"])

    def test_conflict_resolution_stays_in_b_then_can_merge_to_main(self):
        a = self.start("DEMO-12", ["shared.txt", "a.txt"])
        b = self.start("DEMO-13", ["shared.txt"])
        self.commit(a, "a.txt", "A unrelated\n")
        a_head = self.commit(a, "shared.txt", "A implementation\n")
        b_head = self.commit(b, "shared.txt", "B implementation\n")
        self.git("push", "origin", "codex/demo-12", cwd=a)
        a_merge = self.merge_to_origin("DEMO-12")
        result = workspaces.sync_task(b, "DEMO-13", apply=True)
        self.assertEqual(result["status"], "conflicts", result)
        self.assertEqual(result["conflicted_paths"], ["shared.txt"])
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=b), b_head)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=a), a_head)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.writer), a_merge)
        wrong = workspaces.sync_task(b, "DEMO-12", apply=True)
        self.assertEqual(wrong["status"], "blocked")
        self.assertIn("task_branch_mismatch", wrong["blockers"])
        # A's clean incoming file is not adopted into B's scope during resolution.
        self.assertTrue(checkout.write_context(b, "DEMO-13", mode="write", planned_paths=["shared.txt"])["ready"])
        self.assertIn("task_git_operation_in_progress", receipts.check_task(b, "DEMO-13", "merge")["blockers"])
        self.assertFalse(workspaces.sync_task(b, "DEMO-13", apply=True)["ready"])
        (b / "shared.txt").write_text("A implementation plus B implementation\n")
        self.git("add", "shared.txt", cwd=b)
        self.git("commit", "--no-edit", cwd=b)
        self.assertTrue(workspaces.sync_task(b, "DEMO-13", apply=True)["ready"])
        self.assertEqual(checkout.context(b, "DEMO-13")["changed_paths"], ["shared.txt"])
        self.git("push", "origin", "codex/demo-13", cwd=b)
        self.merge_to_origin("DEMO-13")
        self.assertEqual((self.writer / "shared.txt").read_text(), "A implementation plus B implementation\n")
        self.assertEqual((self.writer / "a.txt").read_text(), "A unrelated\n")

    def test_dirty_task_is_not_stashed_or_merged(self):
        b = self.start("DEMO-13")
        (b / "shared.txt").write_text("uncommitted\n")
        with self.assertRaises(sync.WorkflowError):
            workspaces.sync_task(b, "DEMO-13", apply=True)
        self.assertEqual((b / "shared.txt").read_text(), "uncommitted\n")
        self.assertEqual(self.git("stash", "list", cwd=b), "")

    def test_delivery_pushes_only_selected_branch_and_creates_main_pr(self):
        a = self.start("DEMO-12", ["a.txt"])
        b = self.start("DEMO-13", ["b.txt"])
        head = self.commit(a, "a.txt", "A\n")
        (b / "b.txt").write_text("B still developing\n")
        receipts.progress(a, "DEMO-12", update=ready_data(head), expected="missing", apply=True)
        body = self.directory / "report.md"
        body.write_text(receipts.report(a, "DEMO-12", "A delivered"))
        original = workflow.run
        calls = []
        def gh(args, cwd=None, **kwargs):
            if args[0] == "gh":
                calls.append((args, Path(cwd)))
                number = "7" if Path(cwd) == a else "8"
                out = "[]" if args[1:3] == ["pr", "list"] else "https://github.com/example/demo-project/pull/" + number
                return subprocess.CompletedProcess(args, 0, out, "")
            return original(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=gh):
            result = workflow.delivery(a, "DEMO-12", "Task A", body, apply=True)
        create = next(args for args, cwd in calls if args[1:3] == ["pr", "create"])
        self.assertEqual(create[create.index("--base") + 1], "main")
        self.assertEqual(create[create.index("--head") + 1], "codex/demo-12")
        self.assertEqual(result["pr"], "https://github.com/example/demo-project/pull/7")
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/codex/demo-13"), "")
        self.assertEqual((b / "b.txt").read_text(), "B still developing\n")
        b_head = self.commit(b, "b.txt", "B ready\n")
        receipts.progress(b, "DEMO-13", update=ready_data(b_head), expected="missing", apply=True)
        body.write_text(receipts.report(b, "DEMO-13", "B delivered"))
        with patch.object(workflow, "run", side_effect=gh):
            b_result = workflow.delivery(b, "DEMO-13", "Task B", body, apply=True)
        self.assertEqual(b_result["pr"], "https://github.com/example/demo-project/pull/8")
        creates = [args for args, _ in calls if args[1:3] == ["pr", "create"]]
        self.assertEqual([args[args.index("--head") + 1] for args in creates], ["codex/demo-12", "codex/demo-13"])
        self.assertTrue(all(args[args.index("--base") + 1] == "main" for args in creates))
        self.assertEqual(self.git("rev-parse", "main"), self.baseline)

    def test_finishing_a_updates_primary_without_touching_dirty_b(self):
        a = self.start("DEMO-12", ["a.txt"])
        b = self.start("DEMO-13", ["b.txt"])
        a_head = self.commit(a, "a.txt", "accepted A\n")
        b_head = self.commit(b, "b.txt", "B committed\n")
        (b / "b.txt").write_text("B still editing\n")
        self.git("push", "origin", "codex/demo-12", cwd=a)
        merged = self.merge_to_origin("DEMO-12")
        data = ready_data(a_head)
        data["acceptance"] = {"head": a_head, "brief_sha256": receipts.digest(data["brief"]),
                              "evidence": "Fixture user accepted A", "source": source(), "criteria": ["behavior"]}
        data["delivery"] = {"pr_url": "https://github.com/example/demo-project/pull/7", "plane_writeback": "confirmed",
                            "head": a_head, "evidence": "Fixture writeback read back"}
        receipts.progress(a, "DEMO-12", update=data, expected="missing", apply=True)
        pr = {"url": data["delivery"]["pr_url"], "state": "MERGED", "isDraft": False, "headRefOid": a_head,
              "baseRefName": "main", "mergeCommit": {"oid": merged}, "isCrossRepository": False,
              "title": "[DEMO-12] A", "body": "<!-- plane-devflow " + json.dumps(sync.binding(self.cfg, "DEMO-12")) + " -->"}
        original = workflow.run
        def gh(args, cwd=None, **kwargs):
            if args[0] == "gh":
                return subprocess.CompletedProcess(args, 0, json.dumps([] if args[1:3] == ["pr", "checks"] else pr), "")
            return original(args, cwd, **kwargs)
        item = {"task": "DEMO-12", "project_id": self.cfg["plane"]["project_id"], "labels": [],
                "state_group": "completed", "observed_at": datetime.now(timezone.utc).isoformat()}
        with patch.object(workflow, "run", side_effect=gh):
            result = checkout.finish(a, "DEMO-12", workitem=item, apply=True)
        self.assertTrue(result["ready"], result)
        self.assertEqual(self.git("rev-parse", "HEAD"), merged)
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=b), b_head)
        self.assertEqual(self.git("branch", "--show-current", cwd=b), "codex/demo-13")
        self.assertEqual((b / "b.txt").read_text(), "B still editing\n")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=a), a_head)


if __name__ == "__main__":
    unittest.main()
