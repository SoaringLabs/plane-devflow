"""Local new-computer inspection and handoffs do not mutate or authenticate."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_github_setup as fixtures
import first_project
import onboarding
import plane_workflow as workflow


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def status(self, path, **kw):
        real = shutil.which
        with patch.object(first_project, "node_version", return_value=(24, 0, 0)), \
             patch.object(onboarding.shutil, "which", side_effect=lambda name: real("git") if name == "git" else "/synthetic/tool"):
            return first_project.status(path, **kw)

    def test_absent_target_returns_handoff_without_creating_anything(self):
        target = self.root / "My First Project"
        result = self.status(target)
        self.assertFalse(target.exists())
        self.assertEqual(result["next_step"], "prepare_repository")
        self.assertEqual(result["handoff"]["target_directory"], str(target))
        self.assertFalse(result["files_written"])
        self.assertFalse(result["services_called"])

    def test_no_tools_needs_no_repository_or_account(self):
        with patch.object(onboarding.shutil, "which", return_value=None), \
             patch.object(workflow, "run", side_effect=AssertionError("No tool/account calls")):
            result = first_project.status(self.root / "missing")
        self.assertEqual(result["next_step"], "prepare_missing_tools")
        self.assertIsNone(result["checks"]["node_supported"])
        self.assertFalse(result["capabilities"]["codex_cli"])

    def test_nested_folder_does_not_adopt_parent_repository(self):
        workflow.run(["git", "init", "-b", "main"], self.root)
        child = self.root / "new-project"
        child.mkdir()
        result = self.status(child)
        self.assertFalse(result["checks"]["git_repository"])
        self.assertEqual(result["next_step"], "prepare_repository")

    def test_empty_repository_needs_initial_commit(self):
        workflow.run(["git", "init", "-b", "main"], self.root)
        result = self.status(self.root)
        self.assertTrue(result["checks"]["git_repository"])
        self.assertEqual(result["next_step"], "prepare_initial_commit")

    def test_installation_channel_preserves_compatible_plugin_and_runtime(self):
        for channel, expected in (("skills", False), ("plugin", True), ("installed", True)):
            with patch.object(first_project, "node_version", return_value=(20, 19, 0)), \
                 patch.object(onboarding.shutil, "which", return_value="/synthetic/tool"), \
                 patch.object(workflow, "run", side_effect=AssertionError("Absent target needs no Git calls")):
                result = first_project.status(self.root / "missing", channel=channel)
            self.assertEqual(result["next_step"] != "prepare_missing_tools", expected)

    def test_unknown_node_output_is_not_reported_or_executed(self):
        import subprocess
        with patch.object(first_project.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 0, "private unexpected output", "private error")):
            self.assertIsNone(first_project.node_version("node"))

    def test_cli_pre_mapping_runs_without_writes(self):
        script = fixtures.ROOT / "plugins/plane-devflow/scripts/plane_workflow.py"
        result = json.loads(workflow.run([sys.executable, str(script), "bootstrap-status", "--repo",
                                         str(self.root / "not-created")]).stdout)
        self.assertFalse(result["files_written"])
        self.assertFalse((self.root / "not-created").exists())


class MappedBootstrapTests(unittest.TestCase):
    setUp = fixtures.RepositoryTests.setUp

    def test_mapping_and_origin_are_rechecked_without_credentials(self):
        workflow.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                      "commit", "--allow-empty", "-m", "Initial"], self.root)
        before = (self.root / ".plane-devflow.json").read_bytes()
        real = workflow.run
        def local_only(args, *a, **kw):
            self.assertEqual(args[0], "git")
            return real(args, *a, **kw)
        with patch.object(first_project, "node_version", return_value=(24, 0, 0)), \
             patch.object(onboarding.shutil, "which", return_value="/synthetic/tool"), \
             patch.object(workflow, "run", side_effect=local_only):
            result = first_project.status(self.root)
            self.assertEqual(result["next_step"], "resume_setup_progress")
            workflow.run(["git", "remote", "set-url", "origin", "https://github.com/other/repo.git"], self.root)
            changed = first_project.status(self.root)
        self.assertEqual(changed["next_step"], "inspect_existing_mapping")
        self.assertEqual((self.root / ".plane-devflow.json").read_bytes(), before)
