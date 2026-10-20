#!/usr/bin/env python3
"""Generate self-contained Skills CLI packages from the canonical plugin sources."""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("plane-setup", "plane-start", "plane-deliver")
HOSTS = ("codex", "claude-code", "cursor", "opencode")
OWNER = "plane-for-codex/build_skills.py"


def expected_files(root, name):
    root = Path(root)
    plugin = root / "plugins/plane-for-codex"
    mapping = {plugin / "skills" / name / "SKILL.md": Path("SKILL.md")}
    for other in NAMES:
        if other != name:
            mapping[plugin / "skills" / other / "SKILL.md"] = Path(f"references/skill-guides/{other}.md")
    for directory, pattern in (("scripts", "*.py"), ("references", "*.md")):
        mapping.update({p: Path(directory) / p.name for p in (plugin / directory).glob(pattern)})
    resources = root / "scripts/standalone-resources"
    mapping.update({p: Path("references") / p.relative_to(resources) for p in resources.rglob("*.md")})

    def relative(target, document):
        return Path(os.path.relpath(target, document.parent)).as_posix()

    def render(source, destination):
        text = source.read_text(encoding="utf-8").replace("$plane-for-codex:", "")
        if source.is_relative_to(plugin):
            for old, new in (("# Set up Plane for Codex", "# Set up Plane"),
                             ("in one Codex project", "for one repository"),
                             ("Codex-managed", "host-managed"),
                             ("current Codex chat", "current agent session"),
                             ("Codex implementation reports", "agent implementation reports"),
                             ("Codex writes implementation", "The agent writes implementation"),
                             ("Existing OAuth is for Codex", "Existing OAuth is for the current agent"),
                             ("Codex 内的", "当前 agent 内的"), ("回到 Codex 中", "回到当前 agent 中")):
                text = text.replace(old, new)

        def link(match):
            target = match.group(2)
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                return match.group(0)
            original = Path(os.path.normpath(source.parent / unquote(parts.path)))
            if original not in mapping:
                raise ValueError(f"Unpackaged reference in {source.name}: {target}")
            path = relative(mapping[original], destination)
            return match.group(1) + path + ("#" + parts.fragment if parts.fragment else "") + ")"

        lines, fence = [], None
        for line in text.splitlines(keepends=True):
            marker = re.match(r"^\s*(`{3,}|~{3,})", line)
            if marker:
                value = marker.group(1)
                if fence is None:
                    fence = value
                elif value[0] == fence[0] and len(value) >= len(fence):
                    fence = None
                lines.append(line)
            else:
                lines.append(line if fence else re.sub(r"(!?\[[^]\n]*\]\()([^\s)]+)\)", link, line))
        text = "".join(lines)
        helper = relative(Path("scripts/plane_workflow.py"), destination)
        text = text.replace("../../scripts/plane_workflow.py", helper)
        text = text.replace("Use the bundled Plane MCP for account access.",
                            "Use the configured Plane MCP for account access.")
        return text.encode()

    files = {target.as_posix(): render(source, target) if source.suffix == ".md" else source.read_bytes()
             for source, target in mapping.items()}
    entry = files["SKILL.md"].decode()
    start = entry.index("\n# ")
    end = entry.index("\n", start + 1)
    routes = ", ".join(f"[{other}](references/skill-guides/{other}.md)" for other in NAMES if other != name)
    introduction = ("\n\nBefore the first local operation or Plane call, read [agent host capabilities](references/host-runtime.md) "
                    "and the active host's guide. Before live Plane calls, read [MCP access](references/mcp.md) when tools are missing, "
                    "connection setup is requested, or authentication fails. Installation alone does not establish account access. "
                    "For another Plane workflow, use its installed skill when available; otherwise read the bundled guide "
                    f"({routes}) and follow only the user's requested scope.")
    files["SKILL.md"] = (entry[:end] + introduction + entry[end:]).encode()
    ui = (plugin / "skills" / name / "agents/openai.yaml").read_text().replace("$plane-for-codex:", "$")
    ui += ('\ndependencies:\n  tools:\n    - type: "mcp"\n      value: "plane"\n'
           '      description: "Plane account and project tools"\n'
           '      transport: "streamable_http"\n      url: "https://mcp.plane.so/http/mcp"\n')
    files["agents/openai.yaml"] = ui.encode()
    files["LICENSE"] = (root / "LICENSE").read_bytes()
    files["distribution.json"] = (json.dumps({"generator": OWNER, "skill": name,
        "version": json.loads((plugin / "plugin.json").read_text())["version"], "hosts": list(HOSTS)}, indent=2) + "\n").encode()
    return files


def generate(root=ROOT, *, check=False):
    root = Path(root).resolve()
    for p in (root / "plugins/plane-for-codex").rglob("*"):
        if p.is_symlink():
            raise ValueError(f"Canonical source contains a symlink: {p}")
    changes = []
    for name in NAMES:
        expected = expected_files(root, name)
        destination = root / "skills" / name
        if (root / "skills").is_symlink() or destination.is_symlink():
            raise ValueError("Generated skill directories must not be symlinks")
        actual = {}
        for p in destination.rglob("*"):
            if p.is_symlink():
                raise ValueError(f"Generated payload contains a symlink: {p}")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                actual[p.relative_to(destination).as_posix()] = p.read_bytes()
        changed = sorted(key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key))
        changes.extend(f"skills/{name}/{key}" for key in changed)
        if not check and changed:
            if actual and json.loads(actual.get("distribution.json", b"{}" )).get("generator") != OWNER:
                raise ValueError(f"Refusing to overwrite an unowned skill: {name}")
            for key in actual.keys() - expected.keys():
                (destination / key).unlink()
            for key, data in expected.items():
                path = destination / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changes = generate(args.root, check=args.check)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({"skills": len(NAMES), "check": args.check, "changed_files": changes}))
    return int(args.check and bool(changes))


if __name__ == "__main__":
    sys.exit(main())
