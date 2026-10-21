import hashlib
import json
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import test_task_progress as fixtures
import plane_workflow as workflow
import task_diagnostics as diagnostics
import task_progress as progress
import sync_health


class DiagnosticsTests(unittest.TestCase):
    setUp = fixtures.TaskProgressTests.setUp
    git = fixtures.TaskProgressTests.git
    save = fixtures.TaskProgressTests.save
    live = fixtures.TaskProgressTests.live
    workitem = fixtures.TaskProgressTests.workitem
    finalized_data = fixtures.TaskProgressTests.finalized_data

    def status(self, **kwargs):
        return diagnostics.status(self.root, "DEMO-12", **kwargs)

    def tree(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}

    def test_default_repeated_diagnosis_never_reads_remote_or_writes_metadata(self):
        self.save(self.finalized_data())
        before = self.tree()
        real_run = workflow.run
        def local_only(args, *a, **kw):
            self.assertNotEqual(args[0], "gh")
            self.assertNotIn("fetch", args)
            return real_run(args, *a, **kw)
        with patch.object(workflow, "run", side_effect=local_only), patch.object(sync_health, "check", side_effect=AssertionError("remote probe")):
            for _ in range(2):
                result = self.status()
                self.assertEqual(result["github"]["status"], "unknown")
                self.assertFalse(result["sync"]["observation"]["cache_written"])
        self.assertEqual(before, self.tree())

    def test_partial_writeback_is_distinct_from_current_pr(self):
        data = self.finalized_data()
        data["delivery"]["plane_writeback"] = "pending"
        self.save(data)
        real_run = workflow.run
        def fake(args, cwd=None, **kw):
            if args[0] == "gh":
                value = self.live(state="OPEN") if args[1:3] == ["pr", "view"] else [{"name": "unit", "bucket": "pending"}]
                return subprocess.CompletedProcess(args, 0, json.dumps(value), "")
            return real_run(args, cwd, **kw)
        with patch.object(workflow, "run", side_effect=fake), patch.object(sync_health, "check", return_value={"observation": {}}):
            result = self.status(refresh=True, workitem=self.workitem())
        self.assertEqual(result["github"]["pr"]["state"], "OPEN")
        self.assertEqual(result["writeback"]["status"], "pending")
        self.assertIn("required_github_checks_not_passed", result["blockers"])
        self.assertIn("delivery_writeback_pending_or_stale", result["blockers"])
        self.assertIsNone(result["github"]["pr"].get("body"))

    def test_refresh_failure_retains_local_facts_and_does_not_write_cache(self):
        self.save()
        before = self.tree()
        real_run = workflow.run
        def fail(args, *a, **kw):
            if args[0] == "gh":
                raise workflow.WorkflowError("Cannot run gh. Check installation.")
            return real_run(args, *a, **kw)
        with patch.object(workflow, "run", side_effect=fail), patch.object(sync_health, "check", side_effect=workflow.WorkflowError("Cannot run gh.")):
            result = self.status(refresh=True)
        self.assertEqual(result["github"]["status"], "unknown")
        self.assertEqual(result["verification"]["head"], self.head)
        self.assertEqual(result["requirements"]["status"], "recorded")
        self.assertEqual(before, self.tree())

    def test_receipts_are_declarations_and_quotes_are_not_reported(self):
        self.save(self.finalized_data())
        result = self.status(workitem=self.workitem())
        self.assertEqual(result["acceptance"]["status"], "current_declaration")
        self.assertFalse(result["merge_authorization"]["human_message_verified"])
        self.assertNotIn("This implementation looks good", json.dumps(result))
        self.assertEqual(result["actions_event"]["status"], "unknown")
        self.assertFalse(result["writeback"]["current_remote_readback"])

    def test_new_head_reports_stale_verification_acceptance_and_authorization(self):
        self.save(self.finalized_data())
        (self.root / "file.txt").write_text("after")
        self.git("add", ".")
        self.git("commit", "-m", "new head")
        result = self.status()
        self.assertEqual(result["verification"]["checks"][0]["freshness"], "stale")
        self.assertEqual(result["acceptance"]["status"], "stale")
        self.assertIn("merge_authorization_missing_or_stale", result["blockers"])

    def test_snapshot_identity_and_age_are_validated_without_losing_local_status(self):
        for change in ({"task": "DEMO-13"}, {"observed_at": (datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat()},
                       {"observed_at": (datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()}):
            result = self.status(workitem={**self.workitem(), **change})
            self.assertEqual(result["plane"]["status"], "unknown")
            self.assertEqual(result["checkout"]["head"], self.head)

    def test_corrupt_receipt_preserved_and_reported(self):
        path = Path(self.save()["record_path"])
        path.write_text("bad")
        result = self.status()
        self.assertIn("task_receipt_unverified", result["blockers"])
        self.assertEqual(path.read_text(), "bad")

    def test_missing_binding_does_not_create_one(self):
        import checkout_workflow
        path = checkout_workflow.metadata_path(self.root, self.cfg, "DEMO-12", "checkouts")
        path.unlink()
        self.assertIn("task_checkout_missing", self.status()["blockers"])
        self.assertFalse(path.exists())

    def test_other_caller_routes_readonly_to_registered_task_without_switching(self):
        import checkout_workflow
        other = self.root.parent / "other"
        self.git("worktree", "add", "-b", "codex/demo-13", str(other))
        result = diagnostics.status(other, "DEMO-12")
        self.assertEqual(Path(result["execution_path"]), self.root.resolve())
        self.assertFalse(result["caller_is_execution_path"])
        self.assertEqual(workflow.run(["git", "branch", "--show-current"], other).stdout.strip(), "codex/demo-13")
        self.assertEqual(result["checkout"]["branch"], "codex/demo-12")

    def test_unavailable_bound_directory_is_unknown_not_implicitly_rebound(self):
        import checkout_workflow
        path = checkout_workflow.metadata_path(self.root, self.cfg, "DEMO-12", "checkouts")
        value = json.loads(path.read_text())
        value["checkout"]["path"] = str(self.root.parent / "gone")
        path.write_text(json.dumps(value))
        before = path.read_bytes()
        self.assertIn("task_checkout_unverified", self.status()["blockers"])
        self.assertEqual(before, path.read_bytes())

    def test_cleanup_and_handoff_are_separate(self):
        data = self.finalized_data()
        data["environment"] = [{"name": "preview", "owner": "agent", "disposition": "cleanup", "evidence": "owned fixture"}]
        self.save(data)
        result = self.status()
        self.assertIn("agent_environment_cleanup_pending", result["blockers"])
        self.assertIn("local_handoff_pending", result["limitations"])
        self.assertFalse(result["environment"]["process_liveness_verified"])

    def test_dirty_and_wrong_branch_are_independently_visible(self):
        self.git("switch", "main")
        (self.root / "file.txt").write_text("unrelated")
        result = self.status()
        self.assertIn("task_branch_mismatch", result["blockers"])
        self.assertIn("uncommitted_changes_not_covered", result["blockers"])
        self.assertEqual((self.root / "file.txt").read_text(), "unrelated")

    def test_cli_renders_json_without_apply_and_preserves_receipts(self):
        self.save()
        before = self.tree()
        completed = subprocess.run([__import__("sys").executable, workflow.__file__, "task-status", "DEMO-12",
                                    "--repo", str(self.root)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["mode"], "local_and_cache")
        self.assertEqual(before, self.tree())

    def test_repository_event_observation_never_becomes_task_writeback_proof(self):
        with patch.object(sync_health, "status", return_value={"event_run_observed": True,
                "observation": {"source": "cached", "probed_at": "2026-10-21T00:00:00Z"}}):
            result = self.status()
        event = result["actions_event"]
        self.assertEqual(event["status"], "repository_event_observed")
        self.assertEqual(event["source"], "cached")
        self.assertFalse(event["task_binding_verified"])
        self.assertFalse(event["task_writeback_verified"])
        self.assertEqual(result["writeback"]["status"], "missing")
