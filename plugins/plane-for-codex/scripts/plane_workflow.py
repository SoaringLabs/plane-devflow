#!/usr/bin/env python3
"""Local setup, Git preparation, delivery reports and offline demo for Plane for Codex."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from plane_sync import (CONFIG_NAME, VERSION, WorkflowError, binding, parse_task,
                        read_config, require, sync_event, validate_config)


def run(args, cwd=None, *, check=True, input_text=None):
    try:
        result = subprocess.run(args, cwd=cwd, input=input_text, capture_output=True, text=True)
    except OSError:
        raise WorkflowError(f"Cannot run {args[0]}. Check installation.") from None
    if check and result.returncode:
        # Git/gh output may contain credential-bearing remotes; report the operation only.
        raise WorkflowError(f"{args[0]} {args[1]} failed (exit {result.returncode}). Inspect repository/authentication state.")
    return result


def repo_root(path):
    return Path(run(["git", "rev-parse", "--show-toplevel"], path).stdout.strip()).resolve()


def github_repo(remote):
    if remote.startswith("git@github.com:"):
        value = remote[len("git@github.com:"):]
    else:
        parsed = urlparse(remote)
        require(parsed.hostname == "github.com", "v1 requires a github.com remote.")
        value = parsed.path.lstrip("/")
    value = value.removesuffix(".git").rstrip("/")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value), "Cannot identify GitHub owner/repo from origin.")
    return value


def actual_repository(root):
    return github_repo(run(["git", "remote", "get-url", "origin"], root).stdout.strip())


def repo_config(path):
    root = repo_root(path)
    config = read_config(root / CONFIG_NAME)
    require(actual_repository(root).lower() == config["github"]["repository"].lower(),
            "Current origin does not match this repository's Plane configuration.")
    return root, config


def doctor(path):
    root = repo_root(path)
    report = {"version": VERSION, "repository_path": str(root),
              "python": sys.version.split()[0], "github_cli": bool(shutil.which("gh")),
              "codex_cli": bool(shutil.which("codex")),
              "branch": run(["git", "branch", "--show-current"], root).stdout.strip(),
              "has_uncommitted_changes": bool(run(["git", "status", "--porcelain"], root).stdout.strip())}
    try:
        report["repository"] = actual_repository(root)
    except WorkflowError:
        report["repository"] = None
    config_path = root / CONFIG_NAME
    if config_path.exists():
        config = read_config(config_path)
        require(report["repository"] and report["repository"].lower() == config["github"]["repository"].lower(),
                "Config repository does not match origin.")
        report.update(configured=True, workspace=config["plane"]["workspace"],
                      project=config["plane"]["project_identifier"], completion=config["completion"]["policy"])
    else:
        report["configured"] = False
    if shutil.which("gh"):
        report["github_authenticated"] = run(["gh", "auth", "status"], check=False).returncode == 0
    report["plane_mcp"] = "Check the bundled Plane MCP connection in Codex; doctor does not read OAuth credentials."
    return report


def write_new_or_same(path, content):
    if path.exists():
        require(path.read_text() == content, f"{path.name} already contains different settings. Inspect and edit it explicitly.")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def configure(args):
    root = repo_root(args.repo)
    config = validate_config({
        "version": 1,
        "plane": {"api_url": args.api_url, "app_url": args.app_url,
                  "workspace": args.workspace, "project_id": args.project_id,
                  "project_identifier": args.project_key.upper()},
        "github": {"repository": actual_repository(root), "base_branch": args.base,
                   "branch_prefix": args.branch_prefix},
        "states": {"in_progress": args.in_progress, "in_review": args.in_review, "done": args.done},
        "completion": {"policy": args.completion, "manual_label": "manual-acceptance"}})
    content = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    result = {"status": "applied" if args.apply else "planned", "config": config,
              "files": [str(root / CONFIG_NAME)]}
    if args.action_source:
        workflow = caller_workflow(args.action_source)
        result["files"].append(str(root / ".github/workflows/plane-for-codex.yml"))
    # Preflight all files before any write.
    files = [(root / CONFIG_NAME, content)]
    if args.action_source:
        files.append((root / ".github/workflows/plane-for-codex.yml", workflow))
    for path, text in files:
        require(not path.exists() or path.read_text() == text,
                f"{path.name} already contains different settings. Inspect and edit it explicitly.")
    if args.apply:
        result["created"] = [str(path) for path, text in files if write_new_or_same(path, text)]
    return result


def caller_workflow(source):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-fA-F]{40}", source),
            "Pin --action-source to owner/repo@<full 40-character commit SHA>.")
    return f'''# Generated by Plane for Codex. No PR checkout or PR code execution.
name: Plane task sync
on:
  pull_request_target:
    types: [opened, edited, reopened, ready_for_review, converted_to_draft, closed]
permissions:
  contents: read
  pull-requests: read
concurrency:
  group: plane-for-codex-${{{{ github.event.pull_request.number }}}}
  cancel-in-progress: false
jobs:
  sync:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    steps:
      - uses: {source}
        with:
          plane-api-key: ${{{{ secrets.PLANE_API_KEY }}}}
          github-token: ${{{{ github.token }}}}
'''


def branch_name(task, config):
    return f'{config["github"].get("branch_prefix", "codex")}/{parse_task(task, config).lower()}'


def prepare(path, task, *, worktree=None, apply=False):
    root, config = repo_config(path)
    key = parse_task(task, config)
    branch = branch_name(key, config)
    run(["git", "check-ref-format", "--branch", branch], root)
    current = run(["git", "branch", "--show-current"], root).stdout.strip()
    dirty = bool(run(["git", "status", "--porcelain"], root).stdout.strip())
    exists = run(["git", "show-ref", "--verify", "--quiet", "refs/heads/" + branch], root, check=False).returncode == 0
    base = config["github"]["base_branch"]
    remote_base = "refs/remotes/origin/" + base
    if run(["git", "show-ref", "--verify", "--quiet", remote_base], root, check=False).returncode == 0:
        base = "origin/" + base
    run(["git", "rev-parse", "--verify", base + "^{commit}"], root)
    base_sha = run(["git", "rev-parse", base], root).stdout.strip()
    target = Path(worktree).expanduser().resolve() if worktree else root
    if worktree:
        if target.exists():
            existing = run(["git", "rev-parse", "--show-toplevel"], target, check=False)
            require(existing.returncode == 0 and Path(existing.stdout.strip()).resolve() == target,
                    "Worktree path already exists and is not the requested checkout.")
            shared = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], target).stdout.strip()
            common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip()
            require(shared == common and run(["git", "branch", "--show-current"], target).stdout.strip() == branch,
                    "Existing worktree belongs to a different repository or task branch.")
            operation = "resume"
        else:
            operation = "worktree"
    else:
        require(current == branch or not dirty,
                "Current checkout has unrelated changes. Use --worktree to preserve them, or resume its task explicitly.")
        operation = "resume" if current == branch else "switch" if exists else "create"
    result = {"status": "ready" if apply else "planned", "task": key, "branch": branch,
              "path": str(target), "operation": operation, "base": base, "base_sha": base_sha}
    if operation in {"create", "worktree"} and not exists:
        tracked = run(["git", "show", base + ":" + CONFIG_NAME], root, check=False)
        require(tracked.returncode == 0 and json.loads(tracked.stdout) == config,
                "Commit and merge the repository mapping into the base branch before starting a new task branch.")
    if apply:
        if operation == "worktree":
            command = ["git", "worktree", "add"]
            command += [str(target), branch] if exists else ["-b", branch, str(target), base]
            run(command, root)
        elif operation == "create":
            run(["git", "switch", "--create", branch, base], root)
        elif operation == "switch":
            run(["git", "switch", branch], root)
    return result


def render_report(path, task, summary, checks, remaining):
    _, config = repo_config(path)
    task = parse_task(task, config)
    require(bool(summary.strip()), "Delivery summary is required.")
    record = json.dumps(binding(config, task), ensure_ascii=False, separators=(",", ":"))
    return (f"[{task}]\n\n{summary.strip()}\n\n"
            f"## Verification\n\n{checks.strip() or 'No checks recorded.'}\n\n"
            f"## Remaining acceptance\n\n{remaining.strip() or 'No outstanding acceptance steps recorded.'}\n\n"
            f"<!-- plane-for-codex {record} -->\n")


def delivery(path, task, title, body_file, *, apply=False):
    root, config = repo_config(path)
    task = parse_task(task, config)
    branch = run(["git", "branch", "--show-current"], root).stdout.strip()
    require(branch == branch_name(task, config), "Switch to the task branch before delivering.")
    require(not run(["git", "status", "--porcelain"], root).stdout.strip(),
            "Commit the intended task changes before delivery. Unrelated changes should stay outside this checkout.")
    body = Path(body_file).read_text()
    from plane_sync import pr_task
    pr_title = f"[{task}] {title}" if not title.startswith(f"[{task}]") else title
    require(pr_task({"title": pr_title, "body": body}, config) == task, "PR body/task binding mismatch.")
    require(BINDING_MARKER in body, "Use render-report to include the primary task binding.")
    base = config["github"]["base_branch"]
    compare = "origin/" + base
    if run(["git", "rev-parse", "--verify", compare], root, check=False).returncode:
        compare = base
    require(int(run(["git", "rev-list", "--count", compare + "..HEAD"], root).stdout.strip()) > 0,
            "Task branch contains no commits ahead of the base branch.")
    result = {"status": "planned", "task": task, "branch": branch, "base": base,
              "repository": config["github"]["repository"], "title": pr_title}
    if not apply:
        return result
    repo = config["github"]["repository"]
    existing = json.loads(run(["gh", "pr", "list", "--repo", repo, "--head", branch,
                               "--base", base, "--state", "all", "--json", "number,url,state,isCrossRepository"], root).stdout)
    existing = [pr for pr in existing if not pr.get("isCrossRepository", False)]
    require(not any(pr["state"] == "MERGED" for pr in existing),
            "Task branch already has a merged PR. Use explicit finalization or a new task.")
    require(not any(pr["state"] == "CLOSED" for pr in existing),
            "Task branch has a closed PR. Decide whether to reopen it before creating another PR.")
    open_prs = [pr for pr in existing if pr["state"] == "OPEN"]
    require(len(open_prs) <= 1, "Multiple open PRs found for this task branch.")
    run(["git", "push", "--set-upstream", "origin", branch], root)
    if open_prs:
        pr = open_prs[0]
        run(["gh", "pr", "edit", str(pr["number"]), "--repo", repo,
             "--title", pr_title, "--body-file", str(Path(body_file).resolve())], root)
        result.update(status="updated", pr=pr["url"], number=pr["number"])
    else:
        url = run(["gh", "pr", "create", "--repo", repo, "--base", base,
                   "--head", branch, "--title", pr_title, "--body-file", str(Path(body_file).resolve())], root).stdout.strip()
        require(re.fullmatch(r"https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[0-9]+", url), "GitHub returned an unexpected PR URL. Inspect existing PRs before retrying.")
        result.update(status="created", pr=url, number=int(url.rsplit("/", 1)[1]))
    result["plane_writeback"] = "pending: use Plane MCP to write the delivery report and review state"
    return result


BINDING_MARKER = "<!-- plane-for-codex "


def set_secret(path):
    _, config = repo_config(path)
    require(sys.stdin.isatty(), "Run set-secret directly in an interactive terminal, or use GitHub's repository Secrets page.")
    token = getpass.getpass("Plane PAT (hidden; sent only to GitHub repository Secret): ")
    require(bool(token.strip()), "No token supplied.")
    run(["gh", "secret", "set", "PLANE_API_KEY", "--repo", config["github"]["repository"]], input_text=token)
    return {"status": "stored", "secret": "PLANE_API_KEY", "repository": config["github"]["repository"]}


def demo(output=None):
    """Exercise real local Git and sync logic with isolated mock Plane data."""
    directory = Path(output).resolve() if output else Path(tempfile.mkdtemp(prefix="plane-for-codex-demo-"))
    require(not directory.exists() or not any(directory.iterdir()), "Choose an empty demo directory.")
    directory.mkdir(parents=True, exist_ok=True)
    checkout = directory / "repository"
    checkout.mkdir()
    run(["git", "init", "-b", "main"], checkout)
    run(["git", "config", "user.name", "Demo"], checkout)
    run(["git", "config", "user.email", "demo@example.invalid"], checkout)
    run(["git", "remote", "add", "origin", "https://github.com/example/demo-project.git"], checkout)
    project = "11111111-1111-4111-8111-111111111111"
    states = {"in_progress": "22222222-2222-4222-8222-222222222222",
              "in_review": "33333333-3333-4333-8333-333333333333",
              "done": "44444444-4444-4444-8444-444444444444"}
    config = {"version": 1, "plane": {"api_url": "https://api.plane.so", "app_url": "https://app.plane.so",
              "workspace": "example-workspace", "project_id": project, "project_identifier": "DEMO"},
              "github": {"repository": "example/demo-project", "base_branch": "main", "branch_prefix": "codex"},
              "states": states, "completion": {"policy": "on_merge", "manual_label": "manual-acceptance"}}
    (checkout / CONFIG_NAME).write_text(json.dumps(validate_config(config), indent=2) + "\n")
    (checkout / "hello.txt").write_text("Hello\n")
    run(["git", "add", "."], checkout)
    run(["git", "commit", "-m", "Initialize demo"], checkout)
    start = prepare(checkout, "DEMO-1", apply=True)
    resume = prepare(checkout, "DEMO-1", apply=True)
    (checkout / "hello.txt").write_text("Hello, Plane for Codex\n")
    run(["git", "add", "hello.txt"], checkout)
    run(["git", "commit", "-m", "DEMO-1: update greeting"], checkout)
    body = render_report(checkout, "DEMO-1", "Add the project greeting.", "Greeting checked in the isolated demo.", "")
    report_path = directory / "pull-request.md"
    report_path.write_text(body)
    deliver = delivery(checkout, "DEMO-1", "Add the project greeting", report_path)

    class MemoryPlane:
        def __init__(self):
            self.item = {"id": "55555555-5555-4555-8555-555555555555", "project_id": project,
                         "state_id": states["in_progress"], "labels": [], "state": {"group": "started"}}
            self.comments, self.transitions = {}, []

        def work_item(self, task):
            return dict(self.item)

        def update_state(self, item, state):
            self.item["state_id"] = state
            self.transitions.append(state)

        def upsert_comment(self, item, external_id, text):
            self.comments[external_id] = text

    plane = MemoryPlane()
    pr = {"number": 1, "html_url": "https://github.com/example/demo-project/pull/1",
          "title": "[DEMO-1] Add the project greeting", "body": body, "state": "open", "draft": False,
          "base": {"ref": "main", "repo": {"full_name": "example/demo-project"}}}
    event = {"repository": {"full_name": "example/demo-project"}, "pull_request": pr}
    opened = sync_event(event, config, plane)
    run(["git", "switch", "main"], checkout)
    run(["git", "merge", "--ff-only", start["branch"]], checkout)
    pr.update(merged=True, state="closed")
    merged = sync_event(event, config, plane)
    repeated = sync_event(event, config, plane)
    plane.item.update(state_id=states["in_progress"], labels=[{"name": "manual-acceptance"}])
    manual = sync_event(event, config, plane)
    record = {"mode": "offline_demo", "live_services_called": False, "directory": str(directory),
              "start": start, "resume": resume, "delivery": deliver, "pr_open": opened,
              "pr_merged": merged, "repeat_merge": repeated, "manual_acceptance": manual,
              "lifecycle_comment_count": len(plane.comments), "report": str(report_path)}
    require(resume["operation"] == "resume" and len(plane.comments) == 1 and manual["manual_acceptance"], "Demo invariant failed.")
    (directory / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("doctor", help="Read local repo/config/authentication availability.")
    p.add_argument("--repo", default=".")
    p = sub.add_parser("configure", help="Plan or write project mapping; IDs are resolved by the setup Skill.")
    p.add_argument("--repo", default=".")
    for key in ("workspace", "project-id", "project-key", "in-progress", "in-review", "done"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--base", default="main")
    p.add_argument("--branch-prefix", default="codex")
    p.add_argument("--api-url", default="https://api.plane.so")
    p.add_argument("--app-url", default="https://app.plane.so")
    p.add_argument("--completion", choices=["on_merge", "manual"], default="manual")
    p.add_argument("--action-source")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("prepare", help="Plan or prepare a task branch/worktree.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--worktree")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("render-report", help="Create a linked PR body from observed results.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--summary-file", required=True)
    p.add_argument("--checks-file", required=True)
    p.add_argument("--remaining-file")
    p.add_argument("--output", required=True)
    p = sub.add_parser("deliver", help="Plan or push and create/update a PR; Plane writeback uses MCP.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("set-secret", help="Read a Plane PAT through hidden terminal input and store it in GitHub.")
    p.add_argument("--repo", default=".")
    p = sub.add_parser("demo", help="Run an isolated end-to-end offline demo; no accounts needed.")
    p.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.repo)
        elif args.command == "configure":
            result = configure(args)
        elif args.command == "prepare":
            result = prepare(args.repo, args.task, worktree=args.worktree, apply=args.apply)
        elif args.command == "render-report":
            text = render_report(args.repo, args.task, Path(args.summary_file).read_text(), Path(args.checks_file).read_text(),
                                 Path(args.remaining_file).read_text() if args.remaining_file else "")
            output = Path(args.output)
            require(not output.exists(), "Report output already exists. Choose another path or edit it explicitly.")
            output.write_text(text)
            result = {"status": "written", "output": str(output.resolve()), "sha256": hashlib.sha256(text.encode()).hexdigest()}
        elif args.command == "deliver":
            result = delivery(args.repo, args.task, args.title, args.body_file, apply=args.apply)
        elif args.command == "set-secret":
            result = set_secret(args.repo)
        else:
            result = demo(args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, TypeError) as error:
        print(f"plane-for-codex: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
