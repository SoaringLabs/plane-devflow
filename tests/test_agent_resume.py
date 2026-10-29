"""Serial host changes preserve real Git workspaces, work in progress and PRs."""
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from test_parallel_tasks import ParallelFixture
import checkout_workflow as checkout
import plane_workflow as workflow
import plane_sync as sync
import task_executions as executions
import task_diagnostics as diagnostics
import task_progress as receipts
import task_workspaces as workspaces
from test_task_progress import ready_data


class AgentResumeTests(ParallelFixture):
    def automatic_prefixes(self):
        self.cfg["github"].pop("branch_prefix")
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        self.git("add", sync.CONFIG_NAME)
        self.git("commit", "-m", "use active agent prefixes")
        self.git("push", "origin", "main")

    def test_each_host_names_new_tasks_and_plan_writes_nothing(self):
        self.automatic_prefixes()
        for number, (host, prefix) in enumerate([("codex", "codex"), ("claude-code", "claude"),
                                               ("cursor", "cursor"), ("opencode", "opencode"),
                                               ("another-host", "agent"), (None, "agent")], 20):
            task = f"DEMO-{number}"
            with self.subTest(host=host):
                plan = workflow.prepare(self.root, task, agent=host)
                self.assertEqual(plan["branch"], f"{prefix}/{task.lower()}")
                self.assertFalse(Path(plan["path"]).exists())
                self.assertEqual(executions.read_execution(self.root, self.cfg, task), (None, "missing"))
                result = workflow.prepare(self.root, task, agent=host, apply=True)
                self.assertEqual(result["branch"], plan["branch"])
                self.assertEqual(checkout.context(result["path"], task)["blockers"], ["task_file_scope_missing"])
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_explicit_legacy_or_custom_prefix_is_preserved(self):
        for prefix in ("codex", "team"):
            self.cfg["github"]["branch_prefix"] = prefix
            self.assertEqual(workflow.branch_name("DEMO-12", self.cfg, agent="claude-code"), f"{prefix}/demo-12")

    def test_claude_resumes_same_worktree_with_staged_unstaged_and_untracked_files(self):
        self.automatic_prefixes()
        first = workflow.prepare(self.root, "DEMO-12", agent="codex", session_id="chat-a", apply=True)
        target = Path(first["execution_path"])
        context = checkout.context(target, "DEMO-12")
        checkout.context(target, "DEMO-12", allowed_paths=["shared.txt", "new.txt"],
                         expected=context["context_sha256"], apply=True)
        (target / "shared.txt").write_text("staged from A\n")
        self.git("add", "shared.txt", cwd=target)
        (target / "shared.txt").write_text("unstaged from A\n")
        (target / "new.txt").write_text("untracked from A\n")
        before = checkout.context(target, "DEMO-12")
        state = [self.git(*args, cwd=target) for args in [("status", "--porcelain"), ("diff",), ("diff", "--cached")]]
        trees = self.git("worktree", "list", "--porcelain")
        second = workflow.prepare(self.root, "DEMO-12", agent="claude-code", session_id="chat-b", apply=True)
        self.assertEqual(second["execution_path"], str(target))
        self.assertEqual(second["branch"], "codex/demo-12")
        self.assertEqual(second["operation"], "resume")
        self.assertEqual(checkout.context(target, "DEMO-12"), before)
        self.assertEqual([self.git(*args, cwd=target) for args in [("status", "--porcelain"), ("diff",), ("diff", "--cached")]], state)
        self.assertEqual(self.git("worktree", "list", "--porcelain"), trees)
        self.assertEqual((target / "new.txt").read_text(), "untracked from A\n")
        self.assertEqual(self.git("stash", "list"), "")
        self.assertTrue(checkout.write_context(target, "DEMO-12", mode="write", planned_paths=["shared.txt"])["ready"])
        self.assertNotEqual(first["execution"]["current"]["id"], second["execution"]["current"]["id"])

    def test_execution_ids_reuse_current_session_or_explicit_id_and_track_new_sessions(self):
        first = workflow.prepare(self.root, "DEMO-12", agent="codex", session_id="chat-a", apply=True)
        execution_id = first["execution"]["current"]["id"]
        same = workflow.prepare(self.root, "DEMO-12", agent="codex", session_id="chat-a", apply=True)
        self.assertEqual(same["execution"]["current"]["id"], execution_id)
        repeated = workflow.prepare(self.root, "DEMO-12", agent="codex", execution_id=execution_id, apply=True)
        self.assertEqual(repeated["execution"]["current"]["id"], execution_id)
        with self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-12", agent="claude-code", execution_id=execution_id, apply=True)
        second = workflow.prepare(self.root, "DEMO-12", agent="codex", session_id="chat-b", apply=True)
        record, _ = executions.read_execution(self.root, self.cfg, "DEMO-12")
        self.assertNotEqual(second["execution"]["current"]["id"], execution_id)
        self.assertEqual([entry["id"] for entry in record["history"]], [execution_id])
        self.assertEqual(record["current"]["agent"], "codex")

    def test_bound_branch_remains_authoritative_after_explicit_prefix_migration(self):
        target = self.start("DEMO-12")
        before = checkout.context(target, "DEMO-12")
        self.automatic_prefixes()
        resumed = workflow.prepare(self.root, "DEMO-12", agent="claude-code", apply=True)
        self.assertEqual(resumed["execution_path"], str(target))
        self.assertEqual(checkout.context(target, "DEMO-12"), before)
        self.assertEqual(workflow.branch_name("DEMO-12", self.cfg, root=target, agent="claude-code"), "codex/demo-12")
        self.assertEqual(diagnostics.status(self.root, "DEMO-12")["execution_path"], str(target))
        future = workflow.prepare(self.root, "DEMO-13", agent="claude-code", apply=True)
        self.assertEqual(future["branch"], "claude/demo-13")
        self.cfg["completion"]["manual_label"] = "different-policy"
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        with self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-12", agent="cursor", apply=True)

    def test_in_place_resume_after_prefix_migration_uses_task_checkout_config(self):
        first = workflow.prepare(self.root, "DEMO-12", agent="codex", in_place=True, apply=True)
        context = checkout.context(self.root, "DEMO-12")
        checkout.context(self.root, "DEMO-12", allowed_paths=["shared.txt", "new.txt"],
                         expected=context["context_sha256"], apply=True)
        head = self.commit(self.root, "shared.txt", "task implementation\n")
        receipts.progress(self.root, "DEMO-12", update=ready_data(head), expected="missing", apply=True)
        before = checkout.context(self.root, "DEMO-12")
        receipt_hash = receipts.progress(self.root, "DEMO-12")["record_sha256"]
        original_id = first["execution"]["current"]["id"]
        self.git("switch", "main")
        self.automatic_prefixes()
        execution_hash = executions.read_execution(self.root, self.cfg, "DEMO-12")[1]
        worktree_paths = {tree["worktree"] for tree in checkout.worktrees(self.root)}
        plan = workflow.prepare(self.root, "DEMO-12", agent="claude-code", in_place=True)
        self.assertEqual(plan["operation"], "switch")
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual(executions.read_execution(self.root, self.cfg, "DEMO-12")[1], execution_hash)

        resumed = workflow.prepare(self.root, "DEMO-12", agent="claude-code", in_place=True, apply=True)
        current = resumed["execution"]["current"]
        self.assertEqual(resumed["execution_path"], str(self.root))
        self.assertEqual(resumed["branch"], "codex/demo-12")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(checkout.context(self.root, "DEMO-12"), before)
        self.assertEqual(receipts.progress(self.root, "DEMO-12")["record_sha256"], receipt_hash)
        self.assertEqual({tree["worktree"] for tree in checkout.worktrees(self.root)}, worktree_paths)
        self.assertEqual(sync.read_config(self.root / sync.CONFIG_NAME)["github"]["branch_prefix"], "codex")
        self.assertEqual(current["agent"], "claude-code")
        self.assertNotEqual(current["id"], original_id)
        record, _ = executions.read_execution(self.root, self.cfg, "DEMO-12")
        self.assertEqual([entry["id"] for entry in record["history"]], [original_id])

        (self.root / "shared.txt").write_text("staged work\n")
        self.git("add", "shared.txt")
        (self.root / "shared.txt").write_text("unstaged work\n")
        (self.root / "new.txt").write_text("untracked work\n")
        changes = [self.git(*args) for args in [("status", "--porcelain"), ("diff",), ("diff", "--cached")]]
        reused = workflow.prepare(self.root, "DEMO-12", agent="claude-code", execution_id=current["id"],
                                  in_place=True, apply=True)
        self.assertEqual(reused["execution"]["current"], current)
        self.assertEqual([self.git(*args) for args in [("status", "--porcelain"), ("diff",), ("diff", "--cached")]], changes)
        self.assertEqual((self.root / "new.txt").read_text(), "untracked work\n")

    def test_in_place_resume_rejects_non_prefix_config_changes_without_new_execution(self):
        workflow.prepare(self.root, "DEMO-12", agent="codex", in_place=True, apply=True)
        before, stamp = executions.read_execution(self.root, self.cfg, "DEMO-12")
        self.git("switch", "main")
        self.cfg["completion"]["manual_label"] = "different-policy"
        self.automatic_prefixes()
        with self.assertRaisesRegex(sync.WorkflowError, "different task mapping"):
            workflow.prepare(self.root, "DEMO-12", agent="claude-code", in_place=True, apply=True)
        self.assertEqual(executions.read_execution(self.root, self.cfg, "DEMO-12"), (before, stamp))

    def test_unrecorded_cross_host_branch_is_recovered_and_ambiguous_branches_stop(self):
        self.automatic_prefixes()
        target = self.directory / "existing claude workspace"
        self.git("worktree", "add", "-b", "claude/demo-12", str(target), "origin/main")
        prepared = workflow.prepare(self.root, "DEMO-12", agent="codex", apply=True)
        self.assertEqual(prepared["execution_path"], str(target))
        self.assertEqual(prepared["branch"], "claude/demo-12")
        self.git("branch", "claude/demo-13", "origin/main")
        self.git("branch", "codex/demo-13", "origin/main")
        with self.assertRaisesRegex(sync.WorkflowError, "Multiple task branches"):
            workflow.prepare(self.root, "DEMO-13", agent="cursor", apply=True)

    def test_changed_host_uses_bound_branch_for_sync_and_updates_existing_pr(self):
        self.automatic_prefixes()
        first = workflow.prepare(self.root, "DEMO-12", agent="claude-code", apply=True)
        target = Path(first["execution_path"])
        context = checkout.context(target, "DEMO-12")
        checkout.context(target, "DEMO-12", allowed_paths=["shared.txt"], expected=context["context_sha256"], apply=True)
        head = self.commit(target, "shared.txt", "implemented\n")
        data = ready_data(head)
        receipts.progress(target, "DEMO-12", update=data, expected="missing", apply=True)
        before = receipts.progress(target, "DEMO-12")["record_sha256"]
        workflow.prepare(self.root, "DEMO-12", agent="codex", apply=True)
        self.assertEqual(receipts.progress(target, "DEMO-12")["record_sha256"], before)
        self.assertTrue(workspaces.sync_task(target, "DEMO-12", apply=True)["ready"])
        body = self.directory / "report.md"
        body.write_text(receipts.report(target, "DEMO-12", "Implemented"))
        calls, original = [], workflow.run
        def gh(args, cwd=None, **kwargs):
            if args[0] != "gh":
                return original(args, cwd, **kwargs)
            calls.append(args)
            output = json.dumps([{"number": 42, "url": "https://github.com/example/demo-project/pull/42",
                                  "state": "OPEN", "isCrossRepository": False}]) if args[1:3] == ["pr", "list"] else ""
            if args[1:3] == ["pr", "view"]:
                output = json.dumps({"isDraft": False})
            return subprocess.CompletedProcess(args, 0, output, "")
        with patch.object(workflow, "run", side_effect=gh):
            result = workflow.delivery(target, "DEMO-12", "Continue original task", body, apply=True)
        listing = next(args for args in calls if args[1:3] == ["pr", "list"])
        self.assertEqual(listing[listing.index("--head") + 1], "claude/demo-12")
        self.assertTrue(any(args[1:3] == ["pr", "edit"] for args in calls))
        self.assertFalse(any(args[1:3] == ["pr", "create"] for args in calls))
        self.assertEqual(result["pr"], "https://github.com/example/demo-project/pull/42")
