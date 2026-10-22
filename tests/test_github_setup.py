"""Observable setup/readiness and read-only verification invariants."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/plane-devflow/scripts"))
import github_setup as setup
import plane_workflow as workflow
import plane_sync as sync
import action_runner as runner


def config():
    return json.loads((ROOT / "examples/plane-devflow.example.json").read_text())


class ReadinessTests(unittest.TestCase):
    def evidence(self):
        return {k: True for k in ("actions_enabled", "workflow_active", "sync_bundle_verified",
                                  "remote_config_matches", "secret_present", "connection_verified")}

    def test_local_files_and_oauth_cannot_mark_setup_complete(self):
        result = setup.assess(config(), local_files=True)
        self.assertEqual(result["initialization"], "partial")
        self.assertEqual(result["github_sync"], "not_ready")
        self.assertTrue(result["required"])

    def test_missing_secret_explains_loss_of_automatic_updates(self):
        evidence = self.evidence()
        evidence["secret_present"] = False
        result = setup.assess(config(), online=evidence)
        self.assertEqual(result["initialization"], "partial")
        self.assertIn("无法自动同步到 Plane", result["impact"])
        self.assertIn("Codex", result["impact"])
        self.assertTrue(result["resume"])

    def test_each_unknown_or_failed_check_is_incomplete(self):
        for key in self.evidence():
            for value in (False, None):
                evidence = self.evidence()
                evidence[key] = value
                with self.subTest(key=key, value=value):
                    self.assertEqual(setup.assess(config(), online=evidence)["initialization"], "partial")

    def test_complete_connection_does_not_fabricate_event_writeback(self):
        result = setup.assess(config(), online=self.evidence())
        self.assertEqual(result["initialization"], "complete")
        self.assertFalse(result["event_run_observed"])

    def test_basic_background_sync_does_not_enable_states(self):
        cfg = config()
        cfg.update(version=2, states={}, status_sync={"enabled": False})
        result = setup.assess(cfg, online=self.evidence())
        self.assertFalse(result["state_sync"])
        self.assertTrue(result["state_note"])


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for args in (("init", "-b", "main"), ("remote", "add", "origin", "https://github.com/example/demo-project.git")):
            workflow.run(["git", *args], self.root)
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(config()))

    def test_plan_and_repeated_apply_preserve_mapping(self):
        before = (self.root / sync.CONFIG_NAME).read_bytes()
        setup.legacy_install(self.root)
        self.assertFalse((self.root / setup.WORKFLOW).exists())
        setup.legacy_install(self.root, apply=True)
        setup.legacy_install(self.root, apply=True)
        self.assertEqual((self.root / sync.CONFIG_NAME).read_bytes(), before)
        for name, data in setup.bundled_files().items():
            self.assertEqual((self.root / name).read_bytes(), data)

    def test_preflight_conflict_does_not_write_other_files(self):
        path = self.root / setup.BUNDLE / "plane_sync.py"
        path.parent.mkdir(parents=True)
        path.write_text("user customization")
        with self.assertRaises(sync.WorkflowError):
            setup.legacy_install(self.root, apply=True)
        self.assertFalse((self.root / setup.WORKFLOW).exists())
        self.assertEqual(path.read_text(), "user customization")

    def test_symlink_destination_rejected(self):
        target = self.root / "unrelated"
        target.write_text("keep")
        path = self.root / setup.BUNDLE / "plane_sync.py"
        path.parent.mkdir(parents=True)
        path.symlink_to(target)
        with self.assertRaises(sync.WorkflowError):
            setup.legacy_install(self.root, apply=True)
        self.assertEqual(target.read_text(), "keep")

    def remote_check(self, *, conclusions=("success",), remote_sha="a" * 40, run_sha="a" * 40, secret=True,
                     secret_updated="2026-10-10T00:00:00Z", run_started="2026-10-10T01:00:00Z",
                     run_branch="main", event_runs=(), remote_files=None):
        real_run = workflow.run
        files = setup.bundled_files() | {sync.CONFIG_NAME: json.dumps(config()).encode()}
        if remote_files is not None:
            files.update(remote_files)
        def fake_run(args, *pos, **kw):
            if args[0] != "gh":
                return real_run(args, *pos, **kw)
            if args[1:3] == ["secret", "list"]:
                data = [{"name": "PLANE_API_KEY", "updatedAt": secret_updated}] if secret else []
            else:
                suffix = args[2].removeprefix("repos/example/demo-project")
                if not suffix:
                    data = {"default_branch": "main"}
                elif suffix == "/commits/main":
                    data = {"sha": remote_sha}
                elif suffix.startswith("/contents/"):
                    name, query = suffix.removeprefix("/contents/").split("?")
                    self.assertEqual(query, "ref=" + remote_sha)
                    data = {"content": base64.b64encode(files[name]).decode()}
                elif suffix == "/actions/permissions":
                    data = {"enabled": True}
                elif suffix == "/actions/workflows/plane-devflow.yml":
                    data = {"state": "active"}
                elif suffix == "/actions/workflows/plane-devflow.yml/runs?per_page=100":
                    data = {"workflow_runs": [{"id": i, "event": "workflow_dispatch", "head_sha": run_sha,
                              "head_branch": run_branch, "conclusion": c, "run_started_at": run_started,
                              "html_url": f"https://github.com/example/demo-project/actions/runs/{i}"}
                              for i, c in enumerate(conclusions, 1)] + list(event_runs)}
                else:
                    self.fail(f"Unexpected GitHub endpoint: {suffix}")
            return subprocess.CompletedProcess(args, 0, json.dumps(data), "")
        with patch.object(workflow, "run", side_effect=fake_run):
            return setup.check(self.root, now=datetime(2026, 10, 10, 2, tzinfo=timezone.utc))

    def test_remote_current_success_is_ready(self):
        self.assertEqual(self.remote_check()["github_sync"], "ready")

    def test_supported_old_bundle_is_ready_with_optional_update(self):
        files = setup.bundled_files()
        files[setup.BUNDLE + "/plane_sync.py"] = files[setup.BUNDLE + "/plane_sync.py"].replace(
            b'VERSION = "0.10.1"', b'VERSION = "0.10.0"')
        result = self.remote_check(remote_files=files)
        self.assertEqual(result["github_sync"], "ready")
        self.assertFalse(result["checks"]["remote_files_match"])
        self.assertTrue(result["checks"]["sync_bundle_verified"])
        self.assertEqual(result["sync_bundle"]["installed_version"], "0.10.0")
        self.assertTrue(result["sync_bundle"]["update_available"])
        self.assertFalse(result["sync_bundle"]["upgrade_required"])

    def test_old_success_does_not_cover_current_commit(self):
        self.assertEqual(self.remote_check(run_sha="b" * 40)["initialization"], "partial")

    def test_successful_pr_target_on_pr_head_is_observed(self):
        # GitHub records the PR head here, even when the workflow checks out its trusted base.
        event = {"event": "pull_request_target", "head_sha": "b" * 40,
                 "head_branch": "feature/task", "conclusion": "success"}
        result = self.remote_check(event_runs=[event])
        self.assertTrue(result["event_run_observed"])
        self.assertTrue(result["evidence"]["event_run_observed"])
        self.assertEqual(result["github_sync"], "ready")
        self.assertIn("实际写入结果仍需分别核对", result["verification_limit"])

    def test_other_events_and_unsuccessful_pr_targets_are_not_observed(self):
        for event, conclusion in (("push", "success"), ("workflow_dispatch", "success"),
                                  ("pull_request", "success"), ("pull_request_target", "failure"),
                                  ("pull_request_target", "cancelled"), ("pull_request_target", None)):
            with self.subTest(event=event, conclusion=conclusion):
                result = self.remote_check(event_runs=[{"event": event, "conclusion": conclusion,
                    "head_sha": "b" * 40, "head_branch": "feature/task"}])
                self.assertFalse(result["event_run_observed"])

    def test_pr_observation_does_not_relax_connection_verification(self):
        event = {"event": "pull_request_target", "head_sha": "a" * 40,
                 "head_branch": "main", "conclusion": "success"}
        for overrides in ({"run_sha": "b" * 40}, {"run_branch": "feature/task"},
                          {"conclusions": ()}, {"conclusions": ("success", "failure")},
                          {"secret_updated": "2026-10-10T02:00:00Z"}):
            with self.subTest(overrides=overrides):
                result = self.remote_check(event_runs=[event], **overrides)
                self.assertTrue(result["event_run_observed"])
                self.assertFalse(result["evidence"]["connection_verified"])
                self.assertEqual(result["initialization"], "partial")

    def test_new_failure_supersedes_old_success(self):
        self.assertEqual(self.remote_check(conclusions=("success", "failure"))["initialization"], "partial")

    def test_secret_missing_keeps_verified_files_incomplete(self):
        self.assertEqual(self.remote_check(secret=False)["initialization"], "partial")

    def test_secret_replacement_invalidates_older_connection_check(self):
        self.assertEqual(self.remote_check(secret_updated="2026-10-10T02:00:00Z")["initialization"], "partial")

    def test_connection_timestamp_offsets_compare_instants(self):
        self.assertEqual(self.remote_check(secret_updated="2026-10-10T02:30:00+02:00")["github_sync"], "ready")
        self.assertEqual(self.remote_check(secret_updated="2026-10-10T02:30:00+01:00")["initialization"], "partial")
        self.assertEqual(self.remote_check(run_started="2026-10-10T01:00:00+00:00")["github_sync"], "ready")

    def test_invalid_timestamps_remain_unverified(self):
        for field, stage in (("secret_updated", "secret_metadata"), ("run_started", "connection")):
            for value in ("2026-10-10T00:00:00", "invalid-private-timestamp", 123):
                with self.subTest(field=field, value=value):
                    result = self.remote_check(**{field: value})
                    self.assertEqual(result["initialization"], "partial")
                    self.assertIn({"code": "invalid_response", "stage": stage},
                                  [{"code": item["code"], "stage": item["stage"]} for item in result["issues"]])
                    self.assertNotIn(str(value), json.dumps(result["errors"]))


class ConnectionTests(unittest.TestCase):
    def event(self):
        return {"repository": {"full_name": "example/demo-project", "default_branch": "main"}, "ref": "refs/heads/main"}

    def test_check_reads_only_project_and_all_states(self):
        cfg = config()
        client = MagicMock()
        ids = list(cfg["states"].values())
        client.request.side_effect = [{"id": cfg["plane"]["project_id"]},
            {"results": [{"id": ids[0]}], "next_page_results": True, "next_cursor": "page2"},
            {"results": [{"id": i} for i in ids[1:]], "next_page_results": False}]
        with patch.dict(os.environ, {"PLANE_CONFIG_SHA": "a" * 40}), \
             patch.object(runner, "fetch_config", return_value=cfg), patch.object(runner, "PlaneClient", return_value=client):
            result = runner.check_connection(self.event(), "example/demo-project", "token", "key")
        self.assertFalse(result["writes_performed"])
        self.assertTrue(all(call.args[0] == "GET" for call in client.request.call_args_list))
        client.update_state.assert_not_called()
        client.upsert_comment.assert_not_called()

    def test_non_default_dispatch_rejected_before_credential_use(self):
        event = self.event()
        event["ref"] = "refs/heads/untrusted"
        with patch.object(runner, "fetch_config") as fetch:
            with self.assertRaises(sync.WorkflowError):
                runner.check_connection(event, "example/demo-project", "token", "key")
        fetch.assert_not_called()

    def test_invalid_targets_fail_check(self):
        cfg = config()
        client = MagicMock()
        client.request.side_effect = [{"id": cfg["plane"]["project_id"]}, []]
        with patch.dict(os.environ, {"PLANE_CONFIG_SHA": "a" * 40}), \
             patch.object(runner, "fetch_config", return_value=cfg), patch.object(runner, "PlaneClient", return_value=client):
            with self.assertRaisesRegex(sync.WorkflowError, "targets"):
                runner.check_connection(self.event(), "example/demo-project", "token", "key")


if __name__ == "__main__":
    unittest.main()
