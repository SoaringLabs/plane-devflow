import argparse
import base64
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/plane-for-codex/scripts"))
import plane_sync as sync
import plane_workflow as workflow
import action_runner as action


def config():
    return json.loads((ROOT / "examples/plane-for-codex.example.json").read_text())


def event(cfg=None, **updates):
    cfg = cfg or config()
    pr = {"number": 7, "html_url": "https://github.com/example/demo-project/pull/7",
          "title": "[DEMO-12] Fix greeting", "body": "<!-- plane-for-codex " + json.dumps(sync.binding(cfg, "DEMO-12")) + " -->",
          "state": "open", "draft": False,
          "base": {"ref": "main", "sha": "a" * 40, "repo": {"full_name": "example/demo-project"}}}
    pr.update(updates)
    return {"repository": {"full_name": "example/demo-project"}, "pull_request": pr}


class MemoryPlane:
    def __init__(self, cfg=None):
        cfg = cfg or config()
        self.item = {"id": "55555555-5555-4555-8555-555555555555", "project_id": cfg["plane"]["project_id"],
                     "state_id": cfg["states"]["in_progress"], "state": {"group": "started"}, "labels": []}
        self.transitions, self.comments = [], {}

    def work_item(self, task):
        return copy.deepcopy(self.item)

    def update_state(self, item, state):
        self.item["state_id"] = state
        self.transitions.append(state)

    def upsert_comment(self, item, external_id, text):
        self.comments[external_id] = text


class MappingTests(unittest.TestCase):
    def test_valid(self):
        sync.validate_config(config())

    def test_secret_rejected(self):
        cfg = config()
        cfg["plane"]["api_key"] = "sentinel-secret"
        with self.assertRaises(sync.WorkflowError):
            sync.validate_config(cfg)

    def test_unsafe_origins_rejected(self):
        for url in ["http://api.plane.so", "https://token:secret@api.plane.so", "https://api.plane.so/path", "https://api.plane.so?secret=1"]:
            with self.subTest(url=url), self.assertRaises(sync.WorkflowError):
                sync.validate_url(url)

    def test_local_http_requires_test_flag(self):
        with self.assertRaises(sync.WorkflowError):
            sync.validate_url("http://localhost:1234")
        self.assertEqual(sync.validate_url("http://localhost:1234", allow_localhost=True), "http://localhost:1234")

    def test_invalid_branch_refs(self):
        for ref in ["main..next", "main.lock", "main/", "main//x", "-main"]:
            cfg = config()
            cfg["github"]["base_branch"] = ref
            with self.subTest(ref=ref), self.assertRaises(sync.WorkflowError):
                sync.validate_config(cfg)

    def test_states_distinct(self):
        cfg = config()
        cfg["states"]["in_review"] = cfg["states"]["in_progress"]
        with self.assertRaises(sync.WorkflowError):
            sync.validate_config(cfg)

    def test_task_url_and_case(self):
        self.assertEqual(sync.parse_task("https://app.plane.so/example-workspace/browse/DEMO-12/", config()), "DEMO-12")
        self.assertEqual(sync.parse_task("demo-12", config()), "DEMO-12")

    def test_task_wrong_host_workspace_project(self):
        for task in ["OTHER-12", "DEMO-0", "DEMO-12 DEMO-13", "https://evil.invalid/example-workspace/browse/DEMO-12/",
                     "https://app.plane.so/other/browse/DEMO-12/"]:
            with self.subTest(task=task), self.assertRaises(sync.WorkflowError):
                sync.parse_task(task, config())

    def test_binding_mismatch(self):
        e = event()
        e["pull_request"]["body"] = e["pull_request"]["body"].replace("example-workspace", "other")
        with self.assertRaises(sync.WorkflowError):
            sync.pr_task(e["pull_request"], config())

    def test_multiple_primary_rejected(self):
        e = event()
        e["pull_request"]["body"] += "\n[DEMO-13]"
        with self.assertRaises(sync.WorkflowError):
            sync.pr_task(e["pull_request"], config())


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.client = MemoryPlane(self.cfg)

    def test_open_review_repeat_one_comment(self):
        sync.sync_event(event(), self.cfg, self.client)
        sync.sync_event(event(), self.cfg, self.client)
        self.assertEqual(self.client.transitions, [self.cfg["states"]["in_review"]])
        self.assertEqual(len(self.client.comments), 1)

    def test_merge_on_merge_done(self):
        self.cfg["completion"]["policy"] = "on_merge"
        sync.sync_event(event(merged=True, state="closed"), self.cfg, self.client)
        self.assertEqual(self.client.item["state_id"], self.cfg["states"]["done"])

    def test_merge_manual_review(self):
        result = sync.sync_event(event(merged=True, state="closed"), self.cfg, self.client)
        self.assertTrue(result["manual_acceptance"])
        self.assertEqual(self.client.item["state_id"], self.cfg["states"]["in_review"])

    def test_manual_label_overrides_policy(self):
        self.cfg["completion"]["policy"] = "on_merge"
        self.client.item["labels"] = [{"name": "manual-acceptance"}]
        result = sync.sync_event(event(merged=True), self.cfg, self.client)
        self.assertTrue(result["manual_acceptance"])
        self.assertEqual(self.client.item["state_id"], self.cfg["states"]["in_review"])

    def test_closed_without_merge_preserves(self):
        sync.sync_event(event(state="closed"), self.cfg, self.client)
        self.assertFalse(self.client.transitions)

    def test_completed_cancelled_preserved(self):
        for group in ["completed", "cancelled"]:
            self.client.item["state"]["group"] = group
            sync.sync_event(event(), self.cfg, self.client)
            self.assertFalse(self.client.transitions)

    def test_done_preserved_even_missing_expand(self):
        self.client.item["state_id"] = self.cfg["states"]["done"]
        sync.sync_event(event(draft=True), self.cfg, self.client)
        self.assertFalse(self.client.transitions)

    def test_draft_cannot_regress_review(self):
        self.client.item["state_id"] = self.cfg["states"]["in_review"]
        sync.sync_event(event(draft=True), self.cfg, self.client)
        self.assertFalse(self.client.transitions)

    def test_wrong_repository_rejected(self):
        e = event()
        e["repository"]["full_name"] = "other/repo"
        with self.assertRaises(sync.WorkflowError):
            sync.sync_event(e, self.cfg, self.client)
        self.assertFalse(self.client.comments)

    def test_wrong_project_rejected_without_writes(self):
        self.client.item["project_id"] = "other"
        with self.assertRaises(sync.WorkflowError):
            sync.sync_event(event(), self.cfg, self.client)
        self.assertFalse(self.client.comments)
        self.assertFalse(self.client.transitions)

    def test_skip_unmapped_or_different_base(self):
        for e in [event(title="No task", body=""), event(base={"ref": "develop", "repo": {"full_name": "example/demo-project"}})]:
            self.assertEqual(sync.sync_event(e, self.cfg, self.client)["status"], "skipped")
        self.assertFalse(self.client.comments)

    def test_comment_html_escaped(self):
        sync.sync_event(event(title="[DEMO-12] <script>evil</script>"), self.cfg, self.client)
        text = next(iter(self.client.comments.values()))
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_comment_failure_can_replay_state(self):
        with patch.object(self.client, "upsert_comment", side_effect=sync.WorkflowError("unavailable")):
            with self.assertRaises(sync.WorkflowError):
                sync.sync_event(event(), self.cfg, self.client)
        sync.sync_event(event(), self.cfg, self.client)
        self.assertEqual(len(self.client.transitions), 1)
        self.assertEqual(len(self.client.comments), 1)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.client = sync.PlaneClient(config(), "sentinel-secret", sleep=MagicMock())
        self.opener = MagicMock()
        self.client.opener = self.opener

    def response(self, value):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(value).encode()
        return response

    def test_default_v1_task_state_and_v2_comment_routing(self):
        item = MemoryPlane().item
        self.opener.open.return_value = self.response(item)
        self.client.work_item("DEMO-12")
        self.client.update_state(item, config()["states"]["done"])
        self.client.upsert_comment(item, "example/demo-project:pr:7:lifecycle", "<p>ok</p>")
        reqs = [call.args[0] for call in self.opener.open.call_args_list]
        self.assertIn("/api/v1/workspaces/example-workspace/work-items/DEMO-12/", reqs[0].full_url)
        self.assertIn("expand=state%2Clabels", reqs[0].full_url)
        self.assertEqual(json.loads(reqs[1].data), {"state": config()["states"]["done"]})
        self.assertIn("/api/v2/", reqs[2].full_url)
        self.assertEqual(reqs[1].method, "PATCH")
        self.assertTrue(reqs[2].full_url.endswith("/comments/upsert/"))
        self.assertEqual(json.loads(reqs[2].data)["external_source"], "plane-for-codex")
        self.assertEqual(reqs[0].get_header("X-api-key"), "sentinel-secret")

    def test_rate_limit_bounded_retry(self):
        err = HTTPError("https://api.plane.so", 429, "rate", {"Retry-After": "1000"}, io.BytesIO(b"secret"))
        self.opener.open.side_effect = [err, self.response({"ok": True})]
        with self.assertRaisesRegex(sync.WorkflowError, "Retry-After was not shortened"):
            self.client.work_item("DEMO-12")
        self.client.sleep.assert_not_called()
        self.assertEqual(self.opener.open.call_count, 1)

    def test_ambiguous_write_is_not_replayed(self):
        self.opener.open.side_effect = URLError("sentinel-secret")
        with self.assertRaises(sync.WorkflowError) as context:
            self.client.upsert_comment(MemoryPlane().item, "id", "comment")
        self.assertEqual(self.opener.open.call_count, 1)
        self.assertNotIn("sentinel-secret", str(context.exception))

    def test_server_failure_retries_reads_but_never_ambiguous_writes(self):
        for method in ['POST', 'PATCH', 'DELETE']:
            for code in [502, 503, 504]:
                self.opener.open.reset_mock()
                self.client.sleep.reset_mock()
                self.opener.open.side_effect = HTTPError('https://api.plane.so', code, 'private-response', {}, io.BytesIO(b'private-response'))
                with self.subTest(method=method, code=code), self.assertRaisesRegex(sync.WorkflowError, 'ambiguous') as context:
                    self.client.request(method, '/example/', {'name':'fixture'})
                self.assertEqual(self.opener.open.call_count, 1)
                self.client.sleep.assert_not_called()
                self.assertNotIn('private-response', str(context.exception))
        self.opener.open.reset_mock()
        self.opener.open.side_effect = [HTTPError('https://api.plane.so', 503, '', {}, io.BytesIO()), self.response({'ok':True})]
        self.assertEqual(self.client.request('GET', '/example/'), {'ok':True})
        self.assertEqual(self.opener.open.call_count, 2)

    def test_permission_plan_error_sanitized(self):
        for code in [401, 402, 403]:
            self.opener.open.side_effect = HTTPError("https://sentinel-secret@api.plane.so", code, "sentinel-secret", {}, io.BytesIO(b"sentinel-secret"))
            with self.subTest(code=code), self.assertRaises(sync.WorkflowError) as context:
                self.client.work_item("DEMO-12")
            self.assertNotIn("sentinel-secret", str(context.exception))

    def test_redirect_not_followed(self):
        self.assertIsNone(sync.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.invalid"))

    def test_get_network_retry_bounded(self):
        self.opener.open.side_effect = URLError("offline")
        with self.assertRaises(sync.WorkflowError):
            self.client.work_item("DEMO-12")
        self.assertEqual(self.opener.open.call_count, 3)


class GitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/example/demo-project.git")
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(config(), indent=2) + "\n")
        (self.root / "file.txt").write_text("before\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial")

    def git(self, *args):
        return workflow.run(["git", *args], self.root).stdout.strip()

    def task_commit(self):
        workflow.prepare(self.root, "DEMO-12", apply=True)
        (self.root / "file.txt").write_text("after\n")
        self.git("add", "file.txt")
        self.git("commit", "-m", "task")
        body = Path(self.temp.name) / "body.md"
        body.write_text(workflow.render_report(self.root, "DEMO-12", "Update greeting", "Checked", ""))
        return body

    def test_plan_read_only_then_resume(self):
        self.assertEqual(workflow.prepare(self.root, "DEMO-12")["status"], "planned")
        self.assertEqual(self.git("branch", "--show-current"), "main")
        workflow.prepare(self.root, "DEMO-12", apply=True)
        self.assertEqual(workflow.prepare(self.root, "DEMO-12", apply=True)["operation"], "resume")

    def test_dirty_other_branch_not_switched(self):
        (self.root / "file.txt").write_text("unrelated\n")
        with self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-12", apply=True)
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual((self.root / "file.txt").read_text(), "unrelated\n")

    def test_dirty_worktree_isolated_and_resume(self):
        (self.root / "file.txt").write_text("unrelated\n")
        target = Path(self.temp.name) / "task"
        result = workflow.prepare(self.root, "DEMO-12", worktree=target, apply=True)
        self.assertEqual((self.root / "file.txt").read_text(), "unrelated\n")
        self.assertEqual((target / "file.txt").read_text(), "before\n")
        self.assertTrue((target / sync.CONFIG_NAME).exists())
        self.assertEqual(result["operation"], "worktree")
        self.assertEqual(workflow.prepare(self.root, "DEMO-12", worktree=target, apply=True)["operation"], "resume")

    def test_worktree_path_wrong_task_preserved(self):
        target = Path(self.temp.name) / "task"
        workflow.prepare(self.root, "DEMO-12", worktree=target, apply=True)
        with self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-13", worktree=target, apply=True)
        self.assertEqual(workflow.run(["git", "branch", "--show-current"], target).stdout.strip(), "codex/demo-12")

    def test_mapping_missing_in_base_rejected(self):
        self.git("rm", sync.CONFIG_NAME)
        self.git("commit", "-m", "remove mapping")
        (self.root / sync.CONFIG_NAME).write_text(json.dumps(config()))
        with self.assertRaisesRegex(sync.WorkflowError, "Commit and merge"):
            workflow.prepare(self.root, "DEMO-12", worktree=Path(self.temp.name) / "task", apply=True)

    def test_origin_mismatch(self):
        self.git("remote", "set-url", "origin", "https://github.com/other/repo.git")
        with self.assertRaises(sync.WorkflowError):
            workflow.prepare(self.root, "DEMO-12")

    def test_deliver_plan_and_body_binding(self):
        body = self.task_commit()
        result = workflow.delivery(self.root, "DEMO-12", "Greeting", body)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["title"], "[DEMO-12] Greeting")
        self.assertEqual(sync.pr_task({"body": body.read_text()}, config()), "DEMO-12")

    def test_deliver_reuses_open_pr(self):
        body = self.task_commit()
        real_run = workflow.run
        mutations = []
        def fake_run(args, cwd=None, **kwargs):
            if args[0] == "gh":
                mutations.append(args)
                data = [{"number": 7, "url": "https://github.com/example/demo-project/pull/7", "state": "OPEN", "isCrossRepository": False}] if args[1:3] == ["pr", "list"] else ""
                return subprocess.CompletedProcess(args, 0, json.dumps(data) if isinstance(data, list) else data, "")
            if args[1] == "push":
                mutations.append(args)
                return subprocess.CompletedProcess(args, 0, "", "")
            return real_run(args, cwd, **kwargs)
        with patch.object(workflow, "run", side_effect=fake_run):
            result = workflow.delivery(self.root, "DEMO-12", "Greeting", body, apply=True)
        self.assertEqual(result["status"], "updated")
        self.assertTrue(any(args[1:3] == ["pr", "edit"] for args in mutations))
        self.assertFalse(any(args[1:3] == ["pr", "create"] for args in mutations))

    def test_configure_preflight_preserves_files(self):
        cfg = config()
        args = argparse.Namespace(repo=self.root, api_url=cfg["plane"]["api_url"], app_url=cfg["plane"]["app_url"], workspace=cfg["plane"]["workspace"],
            project_id=cfg["plane"]["project_id"], project_key="DEMO", base="main", branch_prefix="codex", completion="manual",
            in_progress=cfg["states"]["in_progress"], in_review=cfg["states"]["in_review"], done=cfg["states"]["done"],
            action_source="example/plugin@" + "a" * 40, apply=True)
        path = self.root / ".github/workflows/plane-for-codex.yml"
        path.parent.mkdir(parents=True)
        path.write_text("existing workflow")
        original = (self.root / sync.CONFIG_NAME).read_text()
        with self.assertRaises(sync.WorkflowError):
            workflow.configure(args)
        self.assertEqual(path.read_text(), "existing workflow")
        self.assertEqual((self.root / sync.CONFIG_NAME).read_text(), original)


class ActionTests(unittest.TestCase):
    def test_pinned_workflow_no_pr_checkout(self):
        text = workflow.caller_workflow("example/plugin@" + "a" * 40)
        self.assertIn("pull_request_target", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertNotIn("actions/checkout", text)
        with self.assertRaises(sync.WorkflowError):
            workflow.caller_workflow("example/plugin@main")

    def test_fetch_config_from_base_sha(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"type": "file", "encoding": "base64", "content": base64.b64encode(json.dumps(config()).encode()).decode()}).encode()
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(action, "build_opener", return_value=opener):
            self.assertEqual(action.fetch_config(event(), "test-token"), config())
        req = opener.open.call_args.args[0]
        self.assertIn("ref=" + "a" * 40, req.full_url)
        self.assertNotIn("test-token", req.full_url)

    def test_current_snapshot_used_before_sync(self):
        cfg = config()
        cfg["completion"]["policy"] = "on_merge"
        client = MemoryPlane(cfg)
        with patch.object(action, "github_snapshot", return_value=event(cfg, merged=True, state="closed")) as snapshot, \
             patch.object(action, "fetch_config", return_value=cfg), patch.object(action, "PlaneClient", return_value=client):
            result = action.run_action(event(cfg), "example/demo-project", "test-token", "plane-key")
        snapshot.assert_called_once()
        self.assertEqual(result["phase"], "merged")
        self.assertEqual(client.item["state_id"], cfg["states"]["done"])

    def test_unmapped_action_skips_without_pat(self):
        e = event(title="Documentation", body="")
        with patch.object(action, "github_snapshot", return_value=e), patch.object(action, "fetch_config", return_value=config()), \
             patch.object(action, "PlaneClient") as client:
            self.assertEqual(action.run_action(e, "example/demo-project", "test-token", None)["status"], "skipped")
        client.assert_not_called()

    def test_event_repo_mismatch_no_network(self):
        with patch.object(action, "github_snapshot") as network:
            with self.assertRaises(sync.WorkflowError):
                action.run_action(event(), "other/repo", "token", "key")
        network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
