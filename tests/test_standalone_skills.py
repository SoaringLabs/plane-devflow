"""Standalone skills remain usable without the repository or companion skills."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_skills
import validate_package


class StandaloneSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        for folder in ("plugins", "scripts/standalone-resources"):
            shutil.copytree(ROOT / folder, self.root / folder,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "LICENSE", self.root / "LICENSE")
        build_skills.generate(self.root)

    def test_generation_is_deterministic_and_check_does_not_repair_drift(self):
        self.assertEqual(build_skills.generate(self.root, check=True), [])
        script = self.root / "skills/plane-start/scripts/plane_sync.py"
        script.write_text(script.read_text() + "\n# local modification\n")
        before = script.read_bytes()
        self.assertTrue(build_skills.generate(self.root, check=True))
        self.assertEqual(script.read_bytes(), before)
        build_skills.generate(self.root)
        self.assertEqual(build_skills.generate(self.root, check=True), [])

    def test_each_skill_can_move_alone_and_run_without_checkout(self):
        version = json.loads((self.root / "plugins/plane-devflow/plugin.json").read_text())["version"]
        for name in build_skills.NAMES:
            destination = Path(self.temp.name) / "installed" / name
            shutil.copytree(self.root / "skills" / name, destination)
        shutil.rmtree(self.root)
        for name in build_skills.NAMES:
            destination = Path(self.temp.name) / "installed" / name
            validate_package.check_links([destination / "SKILL.md", *destination.glob("references/**/*.md")], destination)
            result = subprocess.run([sys.executable, str(destination / "scripts/plane_workflow.py"), "--version"],
                                    cwd=self.temp.name, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), version)
            result = subprocess.run([sys.executable, "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); from github_setup import bundled_files; "
                "assert len(bundled_files()) == 3", str(destination / "scripts")],
                cwd=self.temp.name, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cross_entrypoint_reference_stays_inside_selected_skill(self):
        skill = self.root / "skills/plane-setup"
        reference = (skill / "references/acceptance-environment.md").read_text()
        self.assertIn("skill-guides/plane-deliver.md#record-acceptance-or-finalize", reference)
        self.assertTrue((skill / "references/skill-guides/plane-deliver.md").is_file())
        self.assertEqual(validate_package.validate_standalone(self.root), 3)

    def test_dependency_and_payload_drift_are_rejected(self):
        ui = self.root / "skills/plane-setup/agents/openai.yaml"
        ui.write_text(ui.read_text().replace("https://mcp.plane.so/http/mcp", "https://example.invalid/mcp"))
        with self.assertRaisesRegex(validate_package.ValidationError, "MCP dependency"):
            validate_package.validate_standalone(self.root)

    def test_generator_refuses_unowned_directories_and_symlinks(self):
        marker = self.root / "skills/plane-start/distribution.json"
        marker.write_text(json.dumps({"generator": "somebody-else"}))
        with self.assertRaisesRegex(ValueError, "unowned"):
            build_skills.generate(self.root)
        marker.unlink()
        marker.symlink_to(self.root / "LICENSE")
        with self.assertRaisesRegex(ValueError, "symlink"):
            build_skills.generate(self.root)

    def test_single_skill_inventory_excludes_other_skill_entrypoints(self):
        for name in build_skills.NAMES:
            self.assertEqual(list((self.root / "skills" / name).rglob("SKILL.md")),
                             [self.root / "skills" / name / "SKILL.md"])

    def test_each_skill_contains_four_host_guides_and_neutral_entrypoint(self):
        for name in build_skills.NAMES:
            skill = self.root / "skills" / name
            metadata = json.loads((skill / "distribution.json").read_text())
            self.assertEqual(metadata["hosts"], list(build_skills.HOSTS))
            self.assertEqual({p.stem for p in (skill / "references/hosts").glob("*.md")}, set(build_skills.HOSTS))
            body = (skill / "SKILL.md").read_text()
            self.assertNotIn("../../scripts", body)
            self.assertNotIn("$plane-devflow:", body)
            self.assertIn("references/host-runtime.md", body)
            self.assertNotIn("codex mcp ", (skill / "references/mcp.md").read_text())

    def test_runtime_doctor_works_without_codex_or_github_cli(self):
        project = Path(self.temp.name) / "business"
        project.mkdir()
        git = shutil.which("git")
        subprocess.run([git, "init", "--initial-branch=main", str(project)], check=True, capture_output=True)
        subprocess.run([git, "-C", str(project), "remote", "add", "origin",
                        "https://github.com/example/installation.git"], check=True)
        binaries = Path(self.temp.name) / "bin"
        binaries.mkdir()
        (binaries / "git").symlink_to(git)
        env = {**os.environ, "PATH": str(binaries), "HOME": self.temp.name}
        for name in build_skills.NAMES:
            helper = self.root / "skills" / name / "scripts/plane_workflow.py"
            result = subprocess.run([sys.executable, str(helper), "doctor", "--repo", str(project)],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(report["codex_cli"])
            self.assertFalse(report["github_cli"])
            self.assertFalse(report["configured"])

    def test_missing_host_guide_is_rejected(self):
        (self.root / "skills/plane-start/references/hosts/cursor.md").unlink()
        with self.assertRaisesRegex(validate_package.ValidationError, "Missing resource"):
            validate_package.validate_standalone(self.root)
