#!/usr/bin/env python3
"""Validate portable manifests and referenced files without third-party packages."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/plane-for-codex"
sys.path.insert(0, str(PLUGIN / "scripts"))
from plane_sync import VERSION, validate_config


def validate():
    manifest = json.loads((PLUGIN / "plugin.json").read_text())
    assert manifest["version"] == VERSION
    assert manifest["name"] == "plane-for-codex"
    assert (PLUGIN / manifest["extensions"]["com.openai"]["onboardingSkill"]).is_file()
    mcp = json.loads((PLUGIN / "mcp.json").read_text())
    assert mcp["mcpServers"]["plane"]["url"] == "https://mcp.plane.so/http/mcp"
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    assert (ROOT / marketplace["plugins"][0]["source"]["path"]).resolve() == PLUGIN
    for name in ("plane-setup", "plane-start", "plane-deliver"):
        skill = PLUGIN / "skills" / name / "SKILL.md"
        text = skill.read_text()
        assert text.startswith("---\nname: " + name + "\n")
        assert (skill.parent / "agents/openai.yaml").is_file()
        for target in re.findall(r"\]\(([^)]+)\)", text):
            assert (skill.parent / target.split("#", 1)[0]).is_file(), target
    for example in (ROOT / "examples").glob("plane-for-codex*.json"):
        validate_config(json.loads(example.read_text()))
    assert (ROOT / "action.yml").is_file()
    print("Plugin manifests, versions, Skill references and example mapping valid.")


if __name__ == "__main__":
    validate()
