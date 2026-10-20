#!/usr/bin/env python3
"""Offline source/payload checks. Development dependency: requirements-dev.txt."""
import argparse
import ast
import json
import shlex
from html.parser import HTMLParser
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:
    raise SystemExit("Install development dependencies: python3 -m pip install -r requirements-dev.txt")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/plane-devflow/scripts"))
from plane_sync import validate_config

SKILLS = {"plane-setup", "plane-start", "plane-deliver"}
FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys rather than silently replacing an earlier rule."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        require(isinstance(key, str), "YAML mapping keys must be strings")
        require(key not in result, f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load_yaml(text, label):
    try:
        result = yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise ValidationError(f"{label}: invalid YAML: {error}") from error
    require(isinstance(result, dict), f"{label}: expected a YAML mapping")
    return result


def resource(base, target, boundary):
    path = base / target
    require(not Path(target).is_absolute(), f"Absolute resource path: {target}")
    require(path.resolve().is_relative_to(boundary.resolve()), f"Resource escapes payload: {target}")
    current = path
    while current != boundary and current != current.parent:
        require(not current.is_symlink(), f"Symlink resource: {path}")
        current = current.parent
    require(path.is_file(), f"Missing resource: {path}")
    return path.resolve()


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
    require(match is not None, f"{path}: missing YAML frontmatter")
    data = load_yaml(match.group(1), str(path))
    require(not (data.keys() - FIELDS), f"{path}: unsupported frontmatter fields: {data.keys() - FIELDS}")
    name = data.get("name")
    require(isinstance(name, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is not None
            and len(name) <= 64, f"{path}: invalid skill name")
    require(name == path.parent.name, f"{path}: name must match directory")
    description = data.get("description")
    require(isinstance(description, str) and bool(description.strip()) and len(description) <= 1024,
            f"{path}: description must be a nonempty string of at most 1024 characters")
    for key, limit in (("compatibility", 500), ("license", None), ("allowed-tools", None)):
        if key in data:
            value = data[key]
            require(isinstance(value, str) and bool(value.strip()) and (limit is None or len(value) <= limit),
                    f"{path}: invalid {key}")
    if "metadata" in data:
        require(isinstance(data["metadata"], dict) and all(isinstance(k, str) and isinstance(v, str)
                for k, v in data["metadata"].items()), f"{path}: metadata must map strings to strings")
    require(bool(text[match.end():].strip()), f"{path}: empty skill body")
    return data


def without_fences(text):
    lines, fence = [], None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def anchors(text):
    found, counts = set(), {}
    for heading in re.findall(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", without_fences(text), re.M):
        heading = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"<[^>]*>", "", heading).lower()
        slug = "".join(c for c in heading if c in "_- " or unicodedata.category(c)[0] in "LN").replace(" ", "-")
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        found.add(f"{slug}-{index}" if index else slug)
    found.update(re.findall(r'<a\s+(?:id|name)=[\"\']([^\"\']+)', text))
    return found


class HTMLResources(HTMLParser):
    """Resource-bearing HTML used by GitHub README headers."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.targets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        key = {"a": "href", "img": "src"}.get(tag)
        if key and values.get(key):
            self.targets.append(values[key])


def document_targets(text):
    targets = [m.group(1).strip("<>") for m in re.finditer(
        r"!?\[[^]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+[\"'][^\n]*?[\"'])?\)", text)]
    html = HTMLResources()
    html.feed(text)
    return targets + html.targets


def installation_steps(text):
    blocks = re.findall(r"```(?:sh|bash)\n(.*?)\n```", text, re.S)
    require(bool(blocks), "README needs a primary installation command")
    lexer = shlex.shlex(blocks[0].replace("\\\n", ""), posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    steps = [[]]
    for token in lexer:
        if token == "&&":
            steps.append([])
        else:
            require(token not in (";", "|", "||", "&"), "README installation must stop if a step fails")
            steps[-1].append(token)
    return steps


def check_links(paths, boundary):
    """Inline Markdown and HTML a/img resources; recurse through reached .md files."""
    pending, visited = list(paths), set()
    while pending:
        path = pending.pop().resolve()
        if path in visited:
            continue
        visited.add(path)
        text = without_fences(path.read_text(encoding="utf-8"))
        for target in document_targets(text):
            parts = urlsplit(target)
            if parts.scheme or parts.netloc:
                continue
            dest = resource(path.parent, unquote(parts.path), boundary) if parts.path else path
            if parts.fragment and dest.suffix.lower() == ".md":
                require(unquote(parts.fragment) in anchors(dest.read_text(encoding="utf-8")),
                        f"{path}: missing anchor {target}")
            if dest.suffix.lower() == ".md":
                pending.append(dest)
    return visited


def validate_payload(plugin):
    plugin = Path(plugin).resolve()
    for path in plugin.rglob("*"):
        require(not path.is_symlink(), f"Symlink in payload: {path}")
    manifest = json.loads((plugin / "plugin.json").read_text())
    require(manifest.get("name") == "plane-devflow", "Unexpected plugin name")
    tree = ast.parse((plugin / "scripts/plane_sync.py").read_text())
    versions = [n.value.value for n in tree.body if isinstance(n, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == "VERSION" for t in n.targets) and
                isinstance(n.value, ast.Constant)]
    require(versions == [manifest.get("version")], "Plugin/script version mismatch")
    extension = manifest["extensions"]["com.openai"]
    resource(plugin, extension["onboardingSkill"], plugin)
    for key in ("logo", "composerIcon"):
        resource(plugin, extension["interface"][key], plugin)
    require(extension["interface"]["websiteURL"] == "https://github.com/SoaringLabs/plane-devflow",
            "Plugin website must identify this repository")
    mcp = json.loads((plugin / "mcp.json").read_text())
    require(mcp["mcpServers"]["plane"]["url"] == "https://mcp.plane.so/http/mcp", "Unexpected Plane MCP endpoint")
    directories = {p.name for p in (plugin / "skills").iterdir() if p.is_dir()}
    require(directories == SKILLS, f"Public skill inventory mismatch: {sorted(directories)}")
    for name in sorted(SKILLS):
        skill = plugin / "skills" / name / "SKILL.md"
        frontmatter(skill)
        ui = load_yaml((skill.parent / "agents/openai.yaml").read_text(), name)
        interface = ui.get("interface")
        require(isinstance(interface, dict), f"{name}: missing UI interface")
        for key in ("display_name", "short_description", "default_prompt"):
            require(isinstance(interface.get(key), str) and bool(interface[key].strip()), f"{name}: invalid UI {key}")
        require(len(interface["short_description"]) <= 64, f"{name}: UI description too long")
        require(f"$plane-devflow:{name}" in interface["default_prompt"], f"{name}: UI prompt invokes wrong skill")
        policy = ui.get("policy", {})
        require(isinstance(policy, dict) and ("allow_implicit_invocation" not in policy or
                isinstance(policy["allow_implicit_invocation"], bool)), f"{name}: invalid invocation policy")
        for key in ("icon_small", "icon_large"):
            if key in interface:
                resource(skill.parent, interface[key], plugin)
        resource(skill.parent, "../../scripts/plane_workflow.py", plugin)
    docs = list((plugin / "skills").glob("*/SKILL.md")) + list((plugin / "references").glob("*.md"))
    visited = check_links(docs, plugin)
    return {"skills": len(SKILLS), "markdown_files": len(visited)}


def validate_standalone(root):
    from build_skills import HOSTS, generate
    directory = root / "skills"
    require({p.name for p in directory.iterdir() if p.is_dir()} == SKILLS,
            "Standalone skill inventory mismatch")
    for name in sorted(SKILLS):
        skill = directory / name
        for path in skill.rglob("*"):
            require(not path.is_symlink(), f"Symlink in standalone payload: {path}")
        frontmatter(skill / "SKILL.md")
        ui = load_yaml((skill / "agents/openai.yaml").read_text(), name)
        require(f"${name}" in ui["interface"]["default_prompt"] and
                "$plane-devflow:" not in ui["interface"]["default_prompt"],
                f"{name}: standalone invocation mismatch")
        require(ui.get("dependencies", {}).get("tools") == [{"type": "mcp", "value": "plane",
                "description": "Plane account and project tools", "transport": "streamable_http",
                "url": "https://mcp.plane.so/http/mcp"}], f"{name}: invalid Plane MCP dependency")
        resource(skill, "scripts/plane_workflow.py", skill)
        for host in HOSTS:
            resource(skill, f"references/hosts/{host}.md", skill)
        metadata = json.loads((skill / "distribution.json").read_text())
        require(metadata.get("hosts") == list(HOSTS), f"{name}: host inventory mismatch")
        check_links([skill / "SKILL.md", *skill.glob("references/**/*.md")], skill)
    require(not generate(root, check=True), "Standalone distribution drift; run python3 scripts/build_skills.py")
    return len(SKILLS)


def validate(root=ROOT, *, payload_only=False):
    root = Path(root).resolve()
    plugin = root if payload_only else root / "plugins/plane-devflow"
    result = validate_payload(plugin)
    if not payload_only:
        marketplace = json.loads((root / ".agents/plugins/marketplace.json").read_text())
        entries = marketplace.get("plugins", [])
        require(len(entries) == 1 and entries[0]["name"] == "plane-devflow", "Unexpected marketplace inventory")
        require((root / entries[0]["source"]["path"]).resolve() == plugin, "Marketplace points outside plugin source")
        require((root / "action.yml").is_file() and (root / "LICENSE").is_file(), "Missing Action or license")
        npm = json.loads((root / "package.json").read_text())
        manifest = json.loads((plugin / "plugin.json").read_text())
        require(npm.get("name") == "plane-devflow", "Unexpected npm package name")
        require(npm.get("version") == manifest.get("version"), "npm/plugin version mismatch")
        require(npm.get("bin") == {"plane-devflow": "bin/plane-devflow.mjs"}, "Unexpected npm executable")
        resource(root, npm["bin"]["plane-devflow"], root)
        for example in (root / "examples").glob("plane-devflow*.json"):
            validate_config(json.loads(example.read_text()))
        readmes = [resource(root, name, root) for name in ("README.md", "README.zh-CN.md")]
        docs = readmes + [root / n for n in ("PUBLISHING.md", "CONTRIBUTING.md") if (root / n).is_file()]
        result["repository_markdown_files"] = len(check_links(docs, root))
        for path in readmes:
            text = path.read_text()
            steps = installation_steps(text)
            require(steps == [["npx", "skills", "add", "SoaringLabs/plane-devflow", "--skill",
                    "plane-setup", "plane-start", "plane-deliver"]],
                    f"{path.name}: README Skills CLI installer mismatch")
            for name in SKILLS:
                require(f"`{name}`" in text, f"{path.name}: missing skill identifier: {name}")
        result["standalone_skills"] = validate_standalone(root)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--payload-only", action="store_true", help="--root is an extracted complete plugin directory")
    args = parser.parse_args()
    try:
        result = validate(args.root, payload_only=args.payload_only)
    except (ValidationError, ValueError, OSError, KeyError, TypeError, SyntaxError) as error:
        print(f"Package validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"valid": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
