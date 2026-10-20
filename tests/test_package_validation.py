"""Malformed packages must fail offline, including an extracted install payload."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_package as package
import build_skills


class PackageValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", "node_modules", "__pycache__", "*.pyc", ".venv", "dist", ".plane-devflow.local", ".env*"))
        self.plugin = self.root / "plugins/plane-devflow"
        self.skill = self.plugin / "skills/plane-start/SKILL.md"

    def replace(self, path, old, new):
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def rejects(self, pattern):
        with self.assertRaisesRegex(package.ValidationError, pattern):
            package.validate(self.root)

    def test_source_and_extracted_payload_have_no_checkout_dependency(self):
        self.assertEqual(package.validate(self.root)["skills"], 3)
        payload = Path(self.temp.name) / "install"
        shutil.copytree(self.plugin, payload)
        shutil.rmtree(self.root)
        self.assertEqual(package.validate(payload, payload_only=True)["skills"], 3)
        result = subprocess.run([sys.executable, str(payload / "scripts/plane_workflow.py"), "--help"],
                                cwd=payload.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("check-task", result.stdout)

    def test_frontmatter_required_fields_types_and_limits(self):
        original = self.skill.read_text()
        start = original.index("description:")
        end = original.index("\n", start)
        for value in ("", "null", "false", "[]", "{}", "7", '"' + "x" * 1025 + '"'):
            with self.subTest(value=value[:30]):
                self.skill.write_text(original[:start] + "description: " + value + original[end:])
                self.rejects("description")

    def test_duplicate_and_malformed_yaml_rejected(self):
        original = self.skill.read_text()
        for value in ("name: plane-start\nname: other", "name: [unterminated"):
            with self.subTest(value=value):
                self.skill.write_text(original.replace("name: plane-start", value, 1))
                with self.assertRaises(package.ValidationError):
                    package.validate(self.root)

    def test_name_matches_directory_and_portable_naming(self):
        original = self.skill.read_text()
        for name in ("other", "Plane-Start", "plane--start", "-plane", "x" * 65):
            with self.subTest(name=name):
                self.skill.write_text(original.replace("name: plane-start", "name: " + name, 1))
                self.rejects("name")

    def test_optional_metadata_has_string_values(self):
        self.replace(self.skill, "name: plane-start", "name: plane-start\nmetadata:\n  version: 1")
        self.rejects("metadata")

    def test_missing_and_unexpected_skill_inventory(self):
        shutil.rmtree(self.plugin / "skills/plane-deliver")
        self.rejects("inventory")
        shutil.copytree(self.plugin / "skills/plane-start", self.plugin / "skills/unlisted")
        self.rejects("inventory")

    def test_nested_reference_and_anchor_are_checked(self):
        reference = self.plugin / "references/checkout.md"
        reference.write_text(reference.read_text() + "\n[broken](missing.md)\n")
        self.rejects("Missing resource")
        reference.write_text("# Checkout\n\n[broken](#missing-anchor)\n")
        self.rejects("missing anchor")

    def test_links_inside_fenced_examples_are_not_resources(self):
        self.skill.write_text(self.skill.read_text() + "\n```markdown\n[example](does-not-exist.md)\n```\n")
        build_skills.generate(self.root)
        package.validate(self.root)

    def test_payload_links_cannot_escape_to_repo_files(self):
        self.skill.write_text(self.skill.read_text() + "\n[external](../../../../README.md)\n")
        self.rejects("escapes payload")

    def test_payload_symlink_rejected_even_when_target_exists(self):
        (self.plugin / "references/alias.md").symlink_to(self.plugin / "references/checkout.md")
        self.rejects("Symlink")

    def test_ui_types_and_wrong_invocation_rejected(self):
        ui = self.skill.parent / "agents/openai.yaml"
        original = ui.read_text()
        for old, new in (('"Start Plane Task"', "false"), ("$plane-devflow:plane-start", "$wrong")):
            ui.write_text(original.replace(old, new))
            self.rejects("UI")

    def test_missing_payload_script_and_icon_rejected(self):
        script = self.plugin / "scripts/plane_workflow.py"
        data = script.read_bytes()
        script.unlink()
        self.rejects("Missing resource")
        script.write_bytes(data)
        (self.plugin / "assets/icon.png").unlink()
        self.rejects("Missing resource")

    def test_version_and_marketplace_drift_rejected(self):
        manifest = self.plugin / "plugin.json"
        original = manifest.read_text()
        data = json.loads(original)
        data["version"] = "99.0.0"
        manifest.write_text(json.dumps(data))
        self.rejects("version mismatch")
        manifest.write_text(original)
        marketplace = self.root / ".agents/plugins/marketplace.json"
        data = json.loads(marketplace.read_text())
        data["plugins"][0]["source"]["path"] = "../somewhere"
        marketplace.write_text(json.dumps(data))
        self.rejects("Marketplace")

    def test_readme_install_identity_is_checked(self):
        self.replace(self.root / "README.md", "npx skills add SoaringLabs/plane-devflow", "npx skills add another/repository")
        self.rejects("Skills CLI installer mismatch")

    def test_localized_readme_installation_is_checked(self):
        self.replace(self.root / "README.zh-CN.md", "npx skills add SoaringLabs/plane-devflow", "npx skills add another/repository")
        self.rejects("Skills CLI installer mismatch")

    def test_html_images_and_navigation_are_checked(self):
        hero = self.root / "docs/assets/workflow.svg"
        data = hero.read_bytes()
        hero.unlink()
        self.rejects("Missing resource")
        hero.write_bytes(data)
        self.replace(self.root / "README.md", 'href="#quick-start"', 'href="#missing-section"')
        self.rejects("missing anchor")

    def test_installation_does_not_continue_after_registration_failure(self):
        self.replace(self.root / "README.md", "npx skills add SoaringLabs/plane-devflow", "npx skills add SoaringLabs/plane-devflow ; echo success")
        self.rejects("stop if a step fails")

    def test_cli_failure_is_nonzero_even_with_python_optimization(self):
        self.replace(self.skill, "name: plane-start", "name: invalid--name")
        result = subprocess.run([sys.executable, "-O", str(ROOT / "scripts/validate_package.py"),
                                 "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("validation failed", result.stderr)
        self.assertEqual(result.stdout, "")
