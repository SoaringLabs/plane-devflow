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
import plane_workflow as workflow
import plane_sync as sync
import task_progress as progress


def ready_data(head):
    brief = {"goal": "Add a direct location entry", "scope": ["Details card"], "out_of_scope": ["Reminder card"],
             "scenarios": ["No location", "Saved location", "Cancel", "Save failure"],
             "criteria": [{"id": "behavior", "description": "Cancel preserves data; save persists location",
                           "required": True, "stage": "review"}]}
    receipt = {"head": head, "brief_sha256": progress.digest(brief), "evidence": "Observed isolated save/cancel and failure retry"}
    return {"brief": brief, "design": {"required": False, "status": "not_required", "evidence": "Existing approved pattern",
                                       "brief_sha256": progress.digest(brief)},
            "checks": [{**receipt, "id": "save-cancel", "criteria": ["behavior"], "kind": "test", "status": "passed"}],
            "self_review": {**receipt, "evidence": "Reviewed scoped diff, state coverage, feedback, long text and existing UI"}}


def source():
    return {"kind": "user_message", "reference": "test-chat/message-1", "quote": "This implementation looks good"}


class TaskProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/example/demo-project.git")
        self.cfg = json.loads((ROOT / "examples/plane-for-codex.example.json").read_text())
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        (self.root / "file.txt").write_text("before")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.head = self.git("rev-parse", "HEAD")
        self.git("switch", "--create", "codex/demo-12")
        import checkout_workflow
        checkout_workflow.capture(self.root, self.cfg, "DEMO-12", allowed_paths=["**"], expected="missing", apply=True)
        self.data = ready_data(self.head)

    def git(self, *args):
        return workflow.run(["git", *args], self.root).stdout.strip()

    def save(self, data=None):
        plan = progress.progress(self.root, "DEMO-12", update=self.data if data is None else data)
        return progress.progress(self.root, "DEMO-12", update=self.data if data is None else data,
                                 expected=plan["expected_record_sha256"], apply=True)

    def live(self, state="MERGED", **extra):
        return {"url": "https://github.com/example/demo-project/pull/7", "state": state, "isDraft": False,
                "headRefOid": self.head, "baseRefName": "main", "mergeCommit": {"oid": "a" * 40},
                "title": "[DEMO-12] Location entry", "body": "<!-- plane-for-codex " + json.dumps(sync.binding(self.cfg, "DEMO-12")) + " -->",
                "isCrossRepository": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", **extra}

    def workitem(self):
        return {"task": "DEMO-12", "project_id": self.cfg["plane"]["project_id"], "labels": [],
                "state_group": "started", "observed_at": datetime.now(timezone.utc).isoformat()}

    def finalized_data(self):
        data = copy.deepcopy(self.data)
        receipt = {"head": self.head, "brief_sha256": progress.digest(data["brief"]), "evidence": "Current human confirmation",
                   "source": source()}
        data["acceptance"] = {**receipt, "criteria": ["behavior"]}
        data["merge_authorization"] = receipt
        data["delivery"] = {"pr_url": "https://github.com/example/demo-project/pull/7", "plane_writeback": "confirmed",
                            "head": self.head, "evidence": "Read back the delivery comment"}
        return data

    def check_live(self, stage, pr=None, checks=None, workitem=None):
        real_run = workflow.run
        def fake(args, cwd=None, **kwargs):
            if args[0] == "gh":
                payload = self.live() if pr is None else pr
                if args[1:3] == ["pr", "checks"]:
                    payload = [] if checks is None else checks
                return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")
            return real_run(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fake):
            return progress.check_task(self.root, "DEMO-12", stage, workitem=workitem)

    def test_inspection_and_plan_leave_git_metadata_unchanged(self):
        metadata = self.root / ".git/plane-for-codex/tasks"
        progress.progress(self.root, "DEMO-12")
        progress.progress(self.root, "DEMO-12", update=self.data)
        self.assertFalse(metadata.exists())

    def test_apply_requires_inspected_digest(self):
        with self.assertRaises(sync.WorkflowError):
            progress.progress(self.root, "DEMO-12", update=self.data, apply=True)
        self.assertFalse((self.root / ".git/plane-for-codex/tasks").exists())

    def test_receipt_shared_across_worktrees_but_not_projects(self):
        first = self.save()
        other = Path(self.temp.name) / "worktree"
        self.git("worktree", "add", "-b", "codex/other", str(other))
        self.assertEqual(progress.progress(other, "DEMO-12")["record_sha256"], first["record_sha256"])
        cfg = copy.deepcopy(self.cfg)
        cfg["plane"]["project_id"] = "88888888-8888-4888-8888-888888888888"
        (other / sync.CONFIG_NAME).write_text(json.dumps(cfg))
        self.assertEqual(progress.progress(other, "DEMO-12")["status"], "missing")

    def test_replay_is_idempotent_and_stale_update_preserved(self):
        first = self.save()
        self.assertEqual(self.save()["status"], "unchanged")
        self.save({"environment": []})
        with self.assertRaises(sync.WorkflowError):
            progress.progress(self.root, "DEMO-12", update={"acceptance": None}, expected=first["record_sha256"], apply=True)

    def test_history_retains_previous_facts_not_used_by_gates(self):
        self.save(self.finalized_data())
        current = self.save({"acceptance": None})["record"]
        self.assertIsNotNone(current["history"][0]["data"]["acceptance"])
        self.assertIn("human_acceptance_missing_or_stale", progress.gates(current["data"], self.head, "complete")["blockers"])

    def test_corrupt_record_not_overwritten(self):
        result = self.save()
        path = Path(result["record_path"])
        path.write_text("{bad json")
        with self.assertRaises(sync.WorkflowError):
            self.save()
        self.assertEqual(path.read_text(), "{bad json")

    def test_symlink_record_rejected(self):
        path = Path(self.save()["record_path"])
        path.unlink()
        path.symlink_to(self.root / "file.txt")
        with self.assertRaises(sync.WorkflowError):
            progress.progress(self.root, "DEMO-12")

    def test_missing_requirements_and_visual_confirmation_block_implementation(self):
        self.assertFalse(progress.gates({}, self.head, "implement")["ready"])
        self.data["design"].update(required=True, status="proposed")
        self.assertIn("design_confirmation_required", progress.gates(self.data, self.head, "implement")["blockers"])

    def test_design_approval_is_not_implementation_acceptance(self):
        self.data["design"].update(required=True, status="approved", source=source())
        progress.validate(self.data, updated=self.data)
        self.assertTrue(progress.gates(self.data, self.head, "review")["ready"])
        self.assertIn("human_acceptance_missing_or_stale", progress.gates(self.data, self.head, "complete")["blockers"])

    def test_project_text_cannot_be_acceptance_or_merge_authorization(self):
        for name in ("acceptance", "merge_authorization"):
            data = self.finalized_data()
            data[name]["source"]["kind"] = "plane_comment"
            with self.assertRaises(sync.WorkflowError):
                self.save(data)

    def test_new_commit_invalidates_verification_acceptance_and_merge_authority(self):
        data = self.finalized_data()
        for stage, blocker in [("review", "self_review_missing_or_stale"), ("merge", "merge_authorization_missing_or_stale"),
                               ("complete", "human_acceptance_missing_or_stale")]:
            self.assertIn(blocker, progress.gates(data, "b" * 40, stage)["blockers"])

    def test_changed_requirements_invalidate_existing_receipts(self):
        self.save(self.finalized_data())
        brief = copy.deepcopy(self.data["brief"])
        brief["scenarios"].append("Long location text")
        record = self.save({"brief": brief})["record"]
        self.assertFalse(progress.gates(record["data"], self.head, "review")["ready"])

    def test_sync_success_is_not_application_verification(self):
        self.data["checks"][0]["kind"] = "sync"
        self.assertIn("criterion_unverified:behavior", progress.gates(self.data, self.head, "review")["blockers"])

    def test_failed_check_cannot_be_hidden_by_another_pass(self):
        check = copy.deepcopy(self.data["checks"][0])
        check.update(id="save-failed", status="failed")
        self.data["checks"].append(check)
        self.assertFalse(progress.gates(self.data, self.head, "review")["ready"])

    def test_completion_only_criterion_can_be_delivered_but_blocks_completion(self):
        self.data["brief"]["criteria"].append({"id": "device", "description": "Device location permission", "required": True, "stage": "complete"})
        brief_hash = progress.digest(self.data["brief"])
        self.data["design"]["brief_sha256"] = brief_hash
        self.data["self_review"]["brief_sha256"] = brief_hash
        self.data["checks"][0]["brief_sha256"] = brief_hash
        self.assertTrue(progress.gates(self.data, self.head, "review")["ready"])
        self.assertIn("criterion_unverified:device", progress.gates(self.data, self.head, "complete")["blockers"])

    def test_accepted_limit_requires_human_evidence(self):
        self.data["checks"][0]["status"] = "accepted_limit"
        with self.assertRaises(sync.WorkflowError):
            self.save()
        self.data["checks"][0]["source"] = source()
        self.save()
        self.assertTrue(progress.gates(self.data, self.head, "review")["ready"])

    def test_partial_acceptance_does_not_complete(self):
        data = self.finalized_data()
        data["brief"]["criteria"].append({"id": "visual", "description": "Visual acceptance", "required": True, "stage": "review"})
        brief_hash = progress.digest(data["brief"])
        for name in ("design", "self_review", "acceptance", "merge_authorization"):
            data[name]["brief_sha256"] = brief_hash
        data["checks"][0].update(brief_sha256=brief_hash, criteria=["behavior", "visual"])
        self.save(data)
        self.assertTrue(progress.gates(data, self.head, "review")["ready"])
        self.assertFalse(progress.gates(data, self.head, "complete")["ready"])

    def test_dirty_checkout_cannot_claim_current_commit_checked(self):
        self.save()
        (self.root / "file.txt").write_text("uncommitted")
        self.assertIn("uncommitted_changes_not_covered", progress.check_task(self.root, "DEMO-12", "review")["blockers"])

    def test_wrong_delivery_repository_rejected(self):
        data = self.finalized_data()
        data["delivery"]["pr_url"] = "https://github.com/other/project/pull/7"
        with self.assertRaises(sync.WorkflowError):
            self.save(data)

    def test_live_merge_and_current_plane_task_required_for_completion(self):
        self.save(self.finalized_data())
        self.assertFalse(self.check_live("complete", pr=self.live("CLOSED"), workitem=self.workitem())["ready"])
        self.assertIn("live_plane_task_unverified", self.check_live("complete")["blockers"])
        self.assertTrue(self.check_live("complete", workitem=self.workitem())["ready"])

    def test_live_pr_head_not_local_head_controls_post_squash_completion(self):
        self.save(self.finalized_data())
        (self.root / "file.txt").write_text("squashed")
        self.git("add", "file.txt")
        self.git("commit", "-m", "squash main")
        self.assertTrue(self.check_live("complete", workitem=self.workitem())["ready"])

    def test_manual_label_overrides_on_merge_without_changing_rules(self):
        self.cfg["completion"]["policy"] = "on_merge"
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(self.cfg))
        self.git("add", sync.CONFIG_NAME)
        self.git("commit", "-m", "completion policy")
        self.head = self.git("rev-parse", "HEAD")
        self.data = ready_data(self.head)
        data = self.finalized_data()
        data["acceptance"] = None
        self.save(data)
        self.assertTrue(self.check_live("complete", workitem=self.workitem())["ready"])
        task = self.workitem()
        task["labels"] = ["manual-acceptance"]
        self.assertIn("human_acceptance_missing_or_stale", self.check_live("complete", workitem=task)["blockers"])

    def test_stale_or_cancelled_plane_task_cannot_complete(self):
        self.save(self.finalized_data())
        task = self.workitem()
        task["observed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
        self.assertFalse(self.check_live("complete", workitem=task)["ready"])
        task = self.workitem()
        task["state_group"] = "cancelled"
        self.assertIn("cancelled_task_preserved", self.check_live("complete", workitem=task)["blockers"])

    def test_merge_authorization_separate_from_acceptance_and_required_ci(self):
        data = self.finalized_data()
        data["merge_authorization"] = None
        self.save(data)
        self.assertIn("merge_authorization_missing_or_stale", self.check_live("merge", pr=self.live("OPEN"))["blockers"])
        self.save(self.finalized_data())
        for bucket in ("pending", "fail", "cancel"):
            self.assertFalse(self.check_live("merge", pr=self.live("OPEN"), checks=[{"bucket": bucket}])["ready"])
        self.assertTrue(self.check_live("merge", pr=self.live("OPEN"), checks=[{"bucket": "pass"}])["ready"])

    def test_wrong_project_or_pr_binding_fails_closed(self):
        self.save(self.finalized_data())
        self.assertFalse(self.check_live("complete", pr=self.live(title="[DEMO-13] Other", body=""), workitem=self.workitem())["ready"])
        task = self.workitem()
        task["project_id"] = "other"
        self.assertFalse(self.check_live("complete", workitem=task)["ready"])

    def test_cleanup_pending_blocks_only_agent_resources(self):
        data = self.finalized_data()
        data["environment"] = [{"name": "Metro", "owner": "agent", "disposition": "cleanup", "evidence": "Started isolated test port"}]
        self.assertIn("agent_environment_cleanup_pending", progress.gates(data, self.head, "complete")["blockers"])
        data["environment"][0]["owner"] = "user"
        self.assertNotIn("agent_environment_cleanup_pending", progress.gates(data, self.head, "complete")["blockers"])

    def test_snapshot_report_marks_stale_and_partial_evidence(self):
        self.save(self.finalized_data())
        body = progress.report(self.root, "DEMO-12", "Resulting behavior")
        self.assertIn("Accepted criteria: behavior", body)
        self.assertNotIn("PR unmerged", body)
        (self.root / "file.txt").write_text("later")
        self.git("add", "file.txt")
        self.git("commit", "-m", "later change")
        self.assertIn("stale", progress.report(self.root, "DEMO-12", "Resulting behavior"))

    def test_non_draft_delivery_blocked_before_any_external_write(self):
        workflow.prepare(self.root, "DEMO-12", apply=True)
        (self.root / "file.txt").write_text("task")
        self.git("add", "file.txt")
        self.git("commit", "-m", "task")
        body = Path(self.temp.name) / "report.md"
        body.write_text(workflow.render_report(self.root, "DEMO-12", "Location", "Not run", "Needs testing"))
        with self.assertRaises(sync.WorkflowError):
            workflow.delivery(self.root, "DEMO-12", "Location", body, apply=True)
        self.assertFalse(workflow.delivery(self.root, "DEMO-12", "Location", body, draft=True)["delivery_check"]["ready"])


    def test_old_report_rejected_even_when_current_checks_pass(self):
        workflow.prepare(self.root, "DEMO-12", apply=True)
        (self.root / "file.txt").write_text("task")
        self.git("add", "file.txt")
        self.git("commit", "-m", "task")
        self.head = self.git("rev-parse", "HEAD")
        self.data = ready_data(self.head)
        self.save()
        body = Path(self.temp.name) / "report.md"
        body.write_text(progress.report(self.root, "DEMO-12", "Location entry"))
        self.save({"environment": []})
        with self.assertRaisesRegex(sync.WorkflowError, "stale"):
            workflow.delivery(self.root, "DEMO-12", "Location", body)

    def test_live_pr_head_mismatch_blocks_merge_and_network_failure_blocks_completion(self):
        self.save(self.finalized_data())
        self.assertIn("local_pr_head_mismatch", self.check_live("merge", pr=self.live("OPEN", headRefOid="b" * 40))["blockers"])
        real_run = workflow.run
        def unavailable(args, cwd=None, **kwargs):
            if args[0] == "gh":
                raise sync.WorkflowError("Cannot read PR")
            return real_run(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=unavailable):
            self.assertIn("live_pr_or_checks_unverified", progress.check_task(self.root, "DEMO-12", "complete", workitem=self.workitem())["blockers"])

    def test_pending_writeback_and_required_ci_block_completion(self):
        data = self.finalized_data()
        data["delivery"]["plane_writeback"] = "pending"
        self.save(data)
        self.assertIn("delivery_writeback_pending_or_stale", self.check_live("complete", workitem=self.workitem())["blockers"])
        self.save(self.finalized_data())
        self.assertFalse(self.check_live("complete", checks=[{"bucket": "fail"}], workitem=self.workitem())["ready"])

    def test_basic_and_native_preserve_state_sync_ownership(self):
        for mode in ("basic", "native"):
            cfg = copy.deepcopy(self.cfg)
            if mode == "basic":
                cfg.update(version=2, status_sync={"enabled": False}, states={})
            else:
                cfg["sync"] = {"provider": "native"}
            (self.root / sync.CONFIG_NAME).write_text(json.dumps(cfg))
            self.git("add", sync.CONFIG_NAME)
            self.git("commit", "-m", mode)
            self.data = ready_data(self.git("rev-parse", "HEAD"))
            self.save()
            result = progress.check_task(self.root, "DEMO-12", "review")
            self.assertTrue(result["ready"])
            self.assertFalse(result["state_sync"])

    def test_cli_gates_exit_two_and_record_apply_leaves_checkout_clean(self):
        command = [sys.executable, str(ROOT / "plugins/plane-for-codex/scripts/plane_workflow.py"),
                   "check-task", "DEMO-12", "--repo", str(self.root), "--stage", "review"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ready"])
        patch_file = Path(self.temp.name) / "update.json"
        patch_file.write_text(json.dumps(self.data))
        record_cmd = [sys.executable, str(ROOT / "plugins/plane-for-codex/scripts/plane_workflow.py"),
                      "task-progress", "DEMO-12", "--repo", str(self.root), "--record-file", str(patch_file),
                      "--expected-record-sha256", "missing", "--apply"]
        self.assertEqual(subprocess.run(record_cmd, capture_output=True).returncode, 0)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_draft_delivery_converts_existing_review_pr_and_reuses_it(self):
        workflow.prepare(self.root, "DEMO-12", apply=True)
        (self.root / "file.txt").write_text("task")
        self.git("add", "file.txt")
        self.git("commit", "-m", "task")
        body = Path(self.temp.name) / "draft.md"
        body.write_text(workflow.render_report(self.root, "DEMO-12", "Incomplete", "Not run", "Needs review"))
        real_run = workflow.run
        mutations = []
        def fake(args, cwd=None, **kwargs):
            if args[0] == "gh":
                mutations.append(args)
                payload = [{"number": 7, "url": "https://github.com/example/demo-project/pull/7", "state": "OPEN"}]
                if args[1:3] == ["pr", "view"]:
                    payload = {"isDraft": False}
                return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")
            if args[1] == "push":
                return subprocess.CompletedProcess(args, 0, "", "")
            return real_run(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fake):
            result = workflow.delivery(self.root, "DEMO-12", "Incomplete", body, apply=True, draft=True)
        self.assertTrue(result["draft"])
        self.assertTrue(any(args[1:3] == ["pr", "ready"] and "--undo" in args for args in mutations))
        self.assertFalse(any(args[1:3] == ["pr", "create"] for args in mutations))

    def test_task_record_lock_conflict_preserves_previous_bytes(self):
        result = self.save()
        path = Path(result["record_path"])
        before = path.read_bytes()
        lock = path.parent.parent / "configure.lock"
        lock.write_text("")
        with self.assertRaises(sync.WorkflowError):
            self.save({"acceptance": None})
        self.assertEqual(path.read_bytes(), before)

    def test_unknown_or_credential_fields_rejected(self):
        with self.assertRaises(sync.WorkflowError):
            self.save({"api_key": "sentinel"})
        data = copy.deepcopy(self.data)
        data["checks"][0]["criteria"] = ["unknown"]
        with self.assertRaises(sync.WorkflowError):
            self.save(data)

    def test_ready_existing_draft_is_not_silently_promoted(self):
        workflow.prepare(self.root, "DEMO-12", apply=True)
        (self.root / "file.txt").write_text("task")
        self.git("add", "file.txt")
        self.git("commit", "-m", "task")
        self.head = self.git("rev-parse", "HEAD")
        self.data = ready_data(self.head)
        self.save()
        body = Path(self.temp.name) / "report.md"
        body.write_text(progress.report(self.root, "DEMO-12", "Location"))
        real_run = workflow.run
        mutations = []
        def fake(args, cwd=None, **kwargs):
            if args[0] == "gh":
                mutations.append(args)
                data = [{"number": 7, "url": "https://github.com/example/demo-project/pull/7", "state": "OPEN"}]
                if args[1:3] == ["pr", "view"]:
                    data = {"isDraft": True}
                return subprocess.CompletedProcess(args, 0, json.dumps(data), "")
            if args[1] == "push":
                return subprocess.CompletedProcess(args, 0, "", "")
            return real_run(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fake):
            result = workflow.delivery(self.root, "DEMO-12", "Location", body, apply=True)
        self.assertTrue(result["draft"])
        self.assertFalse(any(args[1:3] == ["pr", "ready"] for args in mutations))

    def test_no_required_checks_diagnostic_supported_but_auth_error_not_accepted(self):
        self.save(self.finalized_data())
        real_run = workflow.run
        diagnostic = "no required checks reported on the 'codex/demo-12' branch\n"
        def fake(args, cwd=None, **kwargs):
            if args[0] == "gh":
                if args[1:3] == ["pr", "checks"]:
                    return subprocess.CompletedProcess(args, 1, "", diagnostic)
                return subprocess.CompletedProcess(args, 0, json.dumps(self.live("OPEN")), "")
            return real_run(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fake):
            self.assertTrue(progress.check_task(self.root, "DEMO-12", "merge")["ready"])
            diagnostic = "HTTP 403: insufficient permission"
            self.assertFalse(progress.check_task(self.root, "DEMO-12", "merge")["ready"])

    def test_blocked_or_unknown_mergeability_does_not_pass_gate(self):
        self.save(self.finalized_data())
        for status in ("BLOCKED", "UNKNOWN", "BEHIND", "DIRTY"):
            result = self.check_live("merge", pr=self.live("OPEN", mergeStateStatus=status))
            self.assertIn("pr_mergeability_unverified_or_blocked", result["blockers"])


if __name__ == "__main__":
    unittest.main()
