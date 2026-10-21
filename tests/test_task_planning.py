"""Draft persistence and partial-create reconciliation; no real account mutations."""
import json
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import test_github_setup as fixtures
import plane_workflow as workflow
from plane_sync import WorkflowError
import task_planning


def draft():
    return {"version": 1, "goal": "First local version", "tasks": [
        {"key": "page", "name": "Build page", "description": "A list; no accounts.",
         "criteria": ["Empty state appears"], "depends_on": []},
        {"key": "save", "name": "Save locally", "description": "Local browser storage only.",
         "criteria": ["Refresh retains data"], "depends_on": ["page"]}]}


def snapshot(items=()):
    return {"project_id": fixtures.config()["plane"]["project_id"],
            "observed_at": datetime.now(timezone.utc).isoformat(), "complete": True, "workitems": list(items)}


def remote(operation):
    return {"id": str(uuid.uuid4()), "project_id": fixtures.config()["plane"]["project_id"],
            **{k: operation[k] for k in ("name", "external_id", "external_source")}}


class TaskPlanningTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def plan(self, **kw):
        return task_planning.progress(self.root, **kw)

    def save(self):
        planned = self.plan(plan=draft())
        return self.plan(plan=draft(), expected=planned["plan_id"], apply=True)

    def test_read_plan_does_not_save_or_make_service_calls(self):
        real = workflow.run
        def git_only(args, *a, **kw):
            self.assertEqual(args[0], "git")
            return real(args, *a, **kw)
        with patch.object(workflow, "run", side_effect=git_only):
            result = self.plan(plan=draft())
        self.assertFalse(result["saved"])
        self.assertFalse(result["remote_writes_performed"])
        self.assertEqual(result["reconciliation"], "pending_live_snapshot")
        self.assertFalse((self.root / ".git/plane-devflow").exists())

    def test_save_requires_reviewed_digest_and_is_idempotent(self):
        with self.assertRaisesRegex(WorkflowError, "digest"):
            self.plan(plan=draft(), expected="0" * 64, apply=True)
        saved = self.save()
        path = task_planning.Path(saved["plan_path"])
        before = path.stat().st_mtime_ns
        self.save()
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertEqual(set(json.loads(path.read_text())), {"version", "config_sha256", "plan_id", "plan"})

    def test_saved_plan_resumes_without_input_and_supplies_no_approval(self):
        saved = self.save()
        result = self.plan(plan_id=saved["plan_id"])
        self.assertEqual(result["plan"], draft())
        self.assertIn("verify_original_user", result["authorization"])
        self.assertNotIn("approved", json.loads(task_planning.Path(saved["plan_path"]).read_text()))

    def test_unknown_fields_cannot_smuggle_state_or_authorization(self):
        for edit in (lambda p: p.update(approved=True), lambda p: p["tasks"][0].update(state="done")):
            plan = draft()
            edit(plan)
            with self.assertRaises(WorkflowError):
                self.plan(plan=plan)

    def test_dependencies_reject_cycles_unknowns_and_duplicates(self):
        for deps in (["save"], ["missing"], ["page", "page"]):
            plan = draft()
            plan["tasks"][0 if deps != ["page", "page"] else 1]["depends_on"] = deps
            with self.subTest(deps=deps), self.assertRaises(WorkflowError):
                self.plan(plan=plan)

    def test_partial_success_or_lost_reply_reuses_confirmed_items(self):
        saved = self.save()
        created = remote(saved["operations"][0])
        result = self.plan(plan_id=saved["plan_id"], existing=snapshot([created]))
        self.assertEqual([o["action"] for o in result["operations"]], ["reuse", "create_after_user_approval"])
        self.assertEqual(result["operations"][0]["existing_id"], created["id"])
        all_created = snapshot([created, remote(result["operations"][1])])
        repeated = self.plan(plan_id=saved["plan_id"], existing=all_created)
        self.assertEqual([o["action"] for o in repeated["operations"]], ["reuse", "reuse"])

    def test_same_title_without_binding_and_duplicate_bindings_block_batch(self):
        planned = self.plan(plan=draft())
        item = remote(planned["operations"][0])
        for items in ([{**item, "external_id": None, "external_source": None}],
                      [item, {**item, "id": str(uuid.uuid4())}]):
            result = self.plan(plan=draft(), existing=snapshot(items))
            self.assertEqual(result["reconciliation"], "blocked")
            self.assertTrue(result["blockers"])

    def test_stale_incomplete_wrong_project_and_sparse_snapshots_fail(self):
        item = remote(self.plan(plan=draft())["operations"][0])
        sparse = dict(item)
        del sparse["external_id"]
        cases = [snapshot([sparse]), {**snapshot(), "complete": False},
                 {**snapshot(), "project_id": str(uuid.uuid4())},
                 {**snapshot(), "observed_at": (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(WorkflowError):
                self.plan(plan=draft(), existing=value)

    def test_mapping_change_cannot_retarget_saved_batch(self):
        saved = self.save()
        config = fixtures.config()
        config["plane"]["project_id"] = str(uuid.uuid4())
        (self.root / ".plane-devflow.json").write_text(json.dumps(config))
        with self.assertRaises(FileNotFoundError):
            self.plan(plan_id=saved["plan_id"])
        new = self.plan(plan=draft())
        self.assertNotEqual(saved["plan_id"], new["plan_id"])
        self.assertTrue(task_planning.Path(saved["plan_path"]).exists())

    def test_snapshot_accepts_utc_z_but_rejects_naive_or_nontext_time(self):
        current = snapshot()
        current['observed_at'] = current['observed_at'].replace('+00:00', 'Z')
        self.assertEqual(self.plan(plan=draft(), existing=current)['reconciliation'], 'checked')
        for value in (None, 42, datetime.now().isoformat()):
            with self.subTest(value=value), self.assertRaises(WorkflowError):
                self.plan(plan=draft(), existing={**snapshot(), 'observed_at': value})

    def test_corrupt_or_symlinked_saved_draft_is_preserved(self):
        saved = self.save()
        path = task_planning.Path(saved["plan_path"])
        original = json.loads(path.read_text())
        original["plan"]["goal"] = "Changed elsewhere"
        path.write_text(json.dumps(original))
        with self.assertRaises(WorkflowError):
            self.plan(plan_id=saved["plan_id"])
        path.unlink()
        other = self.root / "unrelated"
        other.write_text("keep")
        path.symlink_to(other)
        with self.assertRaisesRegex(WorkflowError, "symlink"):
            self.plan(plan=draft())
        self.assertEqual(other.read_text(), "keep")

    def test_plan_does_not_change_state_policy_or_checkout(self):
        before = (self.root / ".plane-devflow.json").read_bytes()
        branch = workflow.run(["git", "branch", "--show-current"], self.root).stdout
        self.save()
        self.assertEqual((self.root / ".plane-devflow.json").read_bytes(), before)
        self.assertEqual(workflow.run(["git", "branch", "--show-current"], self.root).stdout, branch)

    def test_html_is_escaped_and_metadata_is_outside_human_description(self):
        plan = draft()
        plan["tasks"][0]["description"] = "<script>example</script>"
        result = self.plan(plan=plan)
        operation = result["operations"][0]
        self.assertIn("&lt;script&gt;", operation["description_html"])
        self.assertNotIn(operation["external_id"], operation["description_html"])

    def test_cli_can_resume_draft_in_another_process(self):
        saved = self.save()
        script = fixtures.ROOT / "plugins/plane-devflow/scripts/plane_workflow.py"
        result = json.loads(workflow.run([sys.executable, str(script), "task-plan", "--repo", str(self.root),
                                         "--plan-id", saved["plan_id"]]).stdout)
        self.assertEqual(result["plan"], draft())
        self.assertFalse(result["remote_writes_performed"])
