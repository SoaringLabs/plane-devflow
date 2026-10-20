#!/usr/bin/env python3
"""Local setup, Git preparation, delivery reports and offline demo for Plane DevFlow."""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

from plane_sync import (CONFIG_NAME, VERSION, WorkflowError, binding, parse_task,
                        read_config, require, sync_provider, api_version, state_sync_enabled, sync_event, validate_config)


def run(args, cwd=None, *, check=True, input_text=None):
    try:
        result = subprocess.run(args, cwd=cwd, input=input_text, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise WorkflowError(f"{args[0]} timed out. Inspect current state before retrying a write.") from None
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
        report["config_sha256"] = snapshot(config_path)[1]
        try:
            config = read_config(config_path)
            report.update(configured=True, config_valid=True, config_version=config["version"],
                          repository_matches=bool(report["repository"] and report["repository"].lower() ==
                                                  config["github"]["repository"].lower()),
                          workspace=config["plane"]["workspace"], project=config["plane"]["project_identifier"],
                          completion=config["completion"]["policy"], state_sync=state_sync_enabled(config),
                          sync_provider=sync_provider(config), api_version=api_version(config))
        except WorkflowError as error:
            report.update(configured=True, config_valid=False, config_error=str(error))
    else:
        report.update(configured=False, config_sha256="missing")
    if shutil.which("gh"):
        report["github_authenticated"] = run(["gh", "auth", "status"], check=False).returncode == 0
    report["plane_mcp"] = "Check the bundled Plane MCP connection in Codex; doctor does not read OAuth credentials."
    if report.get("config_valid"):
        from github_setup import assess, bundled_files
        files = bundled_files()
        local = all((root / name).is_file() and (root / name).read_bytes() == data for name, data in files.items())
        if sync_provider(config) == "native":
            from github_setup import check
            report["setup"] = check(root)
        else:
            report["setup"] = assess(config, local_files=local)
    return report


def write_new_or_same(path, content):
    if path.exists():
        require(path.read_text() == content, f"{path.name} already contains different settings. Inspect and edit it explicitly.")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def snapshot(path):
    require(not path.is_symlink(), "Configuration must be a regular file, not a symlink.")
    data = path.read_bytes() if path.exists() else None
    return data, hashlib.sha256(data).hexdigest() if data is not None else "missing"


def read_mcp_json(path):
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    return data


def project_options(path, projects_file, workspace_file):
    """Format MCP data for selection; repository names only rank recommendations."""
    root = repo_root(path)
    workspace = read_mcp_json(workspace_file)
    require(isinstance(workspace, dict) and workspace.get("slug"), "Read the connected workspace through MCP first.")
    data = read_mcp_json(projects_file)
    if isinstance(data, dict):
        require(not data.get("next_page_results") and not data.get("has_more") and not data.get("next"),
                "Read all project pages before presenting the selection.")
        data = data.get("results", data.get("data"))
    require(isinstance(data, list), "Expected project list from MCP.")
    try:
        name = actual_repository(root).split("/")[-1]
    except WorkflowError:
        name = root.name
    normalize = lambda value: re.sub(r"[\W_]", "", value.casefold())
    choices = []
    for project in data:
        require(isinstance(project, dict) and all(isinstance(project.get(k), str) for k in ("id", "name", "identifier")),
                "Project list is missing IDs, names or identifiers.")
        uuid.UUID(project["id"])
        if not project.get("archived_at"):
            choices.append({"id": project["id"], "name": project["name"], "identifier": project["identifier"],
                            "recommended": normalize(name) in {normalize(project["name"]), normalize(project["identifier"])}})
    choices.sort(key=lambda p: (not p["recommended"], p["name"].casefold()))
    proposed_key = re.sub(r"[^A-Z0-9]", "", name.upper())[:12] or "PROJECT"
    if not proposed_key[0].isalpha():
        proposed_key = "P" + proposed_key[:11]
    return {"workspace": {k: workspace.get(k) for k in ("slug", "name")}, "projects": choices,
            "can_create": True, "selection_required": True,
            "create_defaults": {"name": name, "identifier": proposed_key}}


@contextmanager
def configuration_lock(root):
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    directory = common / "plane-devflow"
    directory.mkdir(exist_ok=True)
    lock = directory / "configure.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise WorkflowError("Another setup is applying configuration. Retry when it finishes; inspect a stale Git metadata lock before removing it.") from None
    try:
        os.close(fd)
        yield directory
    finally:
        lock.unlink()


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix=".plane-config-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(args):
    root = repo_root(args.repo)
    path = root / CONFIG_NAME
    old_bytes, old_hash = snapshot(path)
    replacing = getattr(args, "replace", False)
    expected = getattr(args, "expected_config_sha256", None)
    if expected is not None:
        require(expected == old_hash, "Configuration changed since the plan. Read it and plan again.")
    old = None
    if old_bytes is not None:
        try:
            old = validate_config(json.loads(old_bytes))
        except (WorkflowError, ValueError, TypeError):
            require(replacing, "Existing configuration is invalid. Use the reconfigure flow; do not delete it.")
    plane = {"api_url": args.api_url, "app_url": args.app_url,
                  "workspace": args.workspace, "project_id": args.project_id,
                  "project_identifier": args.project_key.upper()}
    same_project = old is not None and all(old["plane"][key] == plane[key]
                                          for key in ("api_url", "app_url", "workspace", "project_id"))
    selected_file = getattr(args, "project_file", None)
    workspace_file = getattr(args, "workspace_file", None)
    require(bool(selected_file) == bool(workspace_file), "Provide both MCP project and workspace snapshots.")
    if selected_file:
        project, workspace = read_mcp_json(selected_file), read_mcp_json(workspace_file)
        require(isinstance(project, dict) and isinstance(workspace, dict) and
                project.get("id") == plane["project_id"] and project.get("identifier") == plane["project_identifier"] and
                workspace.get("slug") == plane["workspace"] and not project.get("archived_at") and
                (not project.get("workspace") or not workspace.get("id") or project["workspace"] == workspace["id"]),
                "Selected project/workspace does not match the live MCP snapshots.")
    previous_github = old["github"] if old else {}
    base = args.base or previous_github.get("base_branch")
    if not base:
        ref = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], root, check=False)
        require(ref.returncode == 0, "Resolve the GitHub default branch and pass --base; do not assume main.")
        base = ref.stdout.strip().removeprefix("refs/remotes/origin/")
    states = {key: getattr(args, key, None) for key in ("in_progress", "in_review", "done")}
    require(not any(states.values()) or all(states.values()), "Provide all legacy state targets or none.")
    disabled = getattr(args, "disable_state_sync", False)
    require(not disabled or not any(states.values()), "Do not supply state targets when disabling state sync.")
    if same_project and not any(states.values()) and not disabled:
        config = copy.deepcopy(old)
    elif all(states.values()):
        config = {"version": 1, "states": states}
    else:
        config = {"version": 2, "states": {}, "status_sync": {"enabled": False}}
    config.update(plane=plane,
                  github={"repository": actual_repository(root), "base_branch": base,
                          "branch_prefix": args.branch_prefix or previous_github.get("branch_prefix", "codex")},
                  completion={"policy": args.completion or (old["completion"]["policy"] if old else "manual"),
                              "manual_label": old["completion"].get("manual_label", "manual-acceptance") if old else "manual-acceptance"})
    if old and "sync" in old and "sync" not in config:
        config["sync"] = copy.deepcopy(old["sync"])
    provider = getattr(args, "sync_provider", None)
    version = getattr(args, "api_version", None)
    if provider or version:
        selected = {"provider": provider or sync_provider(config),
                    "api_version": version or api_version(config)}
        if not old or "sync" in config or selected != {"provider": "actions", "api_version": "v1"}:
            config["sync"] = selected
    validate_config(config)
    changed = old != config
    require(old_bytes is None or not changed or replacing,
            "Different configuration exists. Use --replace to plan reconfiguration.")
    if args.apply and old_bytes is not None and changed:
        require(expected is not None, "Apply reconfiguration with --expected-config-sha256 from the reviewed plan.")
    content = old_bytes if old == config else (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode()
    result = {"status": "applied" if args.apply else "planned", "config": config,
              "files": [str(path)], "expected_config_sha256": old_hash,
              "changed": changed, "project_changed": old is not None and not same_project,
              "changes": {key: {"before": old.get(key) if old else None, "after": config.get(key)}
                          for key in set(config) | set(old or {}) if (old or {}).get(key) != config.get(key)},
              "live_selection_checked": bool(selected_file)}
    workflow_path = root / ".github/workflows/plane-devflow.yml"
    workflow_in_base = False
    if changed:
        old_base = old["github"]["base_branch"] if old else config["github"]["base_branch"]
        for ref in ("origin/" + old_base, old_base):
            if run(["git", "cat-file", "-e", ref + ":.github/workflows/plane-devflow.yml"], root, check=False).returncode == 0:
                workflow_in_base = True
    if changed and old is not None:
        branch = run(["git", "branch", "--show-current"], root).stdout.strip()
        old_prefix = old["github"].get("branch_prefix", "codex") + "/" + old["plane"]["project_identifier"].lower() + "-"
        require(not branch.lower().startswith(old_prefix),
                "Reconfigure in the setup/base checkout, not an existing task branch; preserve its original association.")
    require(not (changed and (old_bytes is not None or not state_sync_enabled(config)) and
                 (workflow_path.exists() or workflow_in_base)),
            "Existing event workflow must be disabled in a reviewed GitHub change before replacing this mapping. No files changed.")
    workflow_content = None
    if args.action_source:
        require(state_sync_enabled(config), "Actions setup for new basic mappings is deferred; keep basic mode without a PAT.")
        require(not changed or old_bytes is None, "Configure mapping separately before enabling the event workflow.")
        workflow_content = caller_workflow(args.action_source)
        require(not workflow_path.exists() or workflow_path.read_text() == workflow_content,
                "Existing event workflow differs. Inspect it explicitly.")
        result["files"].append(str(workflow_path))
    if args.apply:
        with configuration_lock(root) as metadata:
            require(snapshot(path)[1] == old_hash, "Configuration changed during setup. Plan again; nothing was replaced.")
            result["created"] = []
            if changed:
                if old_bytes is not None:
                    backups = metadata / "backups"
                    backups.mkdir(exist_ok=True)
                    backup = backups / (old_hash + "-" + uuid.uuid4().hex + ".json")
                    atomic_write(backup, old_bytes)
                    result["backup"] = str(backup)
                require(snapshot(path)[1] == old_hash, "Configuration changed before replacement. Plan again.")
                atomic_write(path, content)
                result["created"].append(str(path))
            if workflow_content is not None:
                write_new_or_same(workflow_path, workflow_content)
        result["state_sync"] = state_sync_enabled(config)
    return result


def caller_workflow(source):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-fA-F]{40}", source),
            "Pin --action-source to owner/repo@<full 40-character commit SHA>.")
    return f'''# Generated by Plane DevFlow. No PR checkout or PR code execution.
name: Plane task sync
on:
  pull_request_target:
    types: [opened, edited, reopened, ready_for_review, converted_to_draft, closed]
permissions:
  contents: read
  pull-requests: read
concurrency:
  group: plane-devflow-${{{{ github.event.pull_request.number }}}}
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


def prepare(path, task, *, worktree=None, in_place=False, apply=False):
    require(not (in_place and worktree), "Choose --in-place or --worktree, not both.")
    if in_place:
        from task_workspaces import workspace_lock
        if apply:
            with workspace_lock(repo_root(path)):
                return _prepare_in_place(path, task, apply=True)
        return _prepare_in_place(path, task)
    from task_workspaces import prepare_workspace
    return prepare_workspace(path, task, worktree=worktree, apply=apply)


def _prepare_in_place(path, task, *, apply=False):
    root, config = repo_config(path)
    head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
    branch = run(["git", "branch", "--show-current"], root).stdout.strip()
    require(branch in {"", config["github"]["base_branch"], branch_name(task, config)},
            "Caller checkout belongs to another task. Use the default isolated workspace.")
    if apply:
        base = config["github"]["base_branch"]
        run(["git", "fetch", "origin", f"refs/heads/{base}:refs/remotes/origin/{base}"], root)
        require(repo_config(root)[1] == config and run(["git", "rev-parse", "HEAD"], root).stdout.strip() == head and
                run(["git", "branch", "--show-current"], root).stdout.strip() == branch,
                "Caller checkout changed during preparation. Inspect before switching branches.")
        if not branch:
            require(run(["git", "merge-base", "--is-ancestor", head, "refs/remotes/origin/" + base], root,
                        check=False).returncode == 0,
                    "Detached checkout has unique commits. Preserve them before naming or changing its task branch.")
    result = _prepare_checkout(root, task, apply=apply)
    result.update(execution_path=str(root), caller_path=str(root), base_freshness="fetched" if apply else "unverified")
    return result


def _prepare_checkout(path, task, *, worktree=None, apply=False):
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
        from checkout_workflow import capture, inspect
        # The immutable starting commit is recorded before any implementation.
        context = capture(target, config, key, base_sha=base_sha if not exists else None)
        context = capture(target, config, key, base_sha=base_sha if not exists else None,
                          expected=context["expected_context_sha256"], apply=True)
        result["checkout_context"] = context
        blockers = inspect(target, config, key)["blockers"]
        require(not any(b != "task_file_scope_missing" for b in blockers),
                "Task checkout or accumulated changes need inspection before resuming. Run task-context.")
    return result


def render_report(path, task, summary, checks, remaining):
    _, config = repo_config(path)
    task = parse_task(task, config)
    require(bool(summary.strip()), "Delivery summary is required.")
    record = json.dumps(binding(config, task), ensure_ascii=False, separators=(",", ":"))
    return (f"[{task}]\n\n{summary.strip()}\n\n"
            f"## Verification\n\n{checks.strip() or 'No checks recorded.'}\n\n"
            f"## Remaining acceptance\n\n{remaining.strip() or 'No outstanding acceptance steps recorded.'}\n\n"
            f"<!-- plane-devflow {record} -->\n")


def delivery(path, task, title, body_file, *, apply=False, draft=False):
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
    from task_progress import check_task
    gate = check_task(root, task, "review")
    result.update(delivery_check=gate, draft=draft)
    require(not gate["checkout_check"]["blockers"],
            "Task branch, checkout or file scope changed. Inspect task-context before any delivery, including Drafts.")
    require(draft or gate["ready"], "Task is not ready for acceptance. Inspect check-task --stage review; deliver --draft for incomplete work.")
    if not draft:
        from task_progress import progress, digest, verify_report
        receipt = progress(root, task)
        verify_report(body, receipt["record_sha256"], gate["head"], digest(receipt["record"]["data"]["brief"]))
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
    require(run(["git", "rev-parse", "HEAD"], root).stdout.strip() == gate["head"] and
            run(["git", "branch", "--show-current"], root).stdout.strip() == branch and
            not run(["git", "status", "--porcelain"], root).stdout.strip(),
            "Task checkout changed during delivery. Inspect and rerun its gate.")
    from task_progress import progress
    require(progress(root, task)["record_sha256"] == gate["record_sha256"],
            "Task evidence changed during delivery. Regenerate the report before pushing.")
    from checkout_workflow import inspect
    checkout = inspect(root, config, task)
    require(checkout["ready"] and checkout["context_sha256"] == gate["checkout_check"]["context_sha256"],
            "Task checkout/scope changed during delivery. Inspect before pushing.")
    if open_prs:
        pr = open_prs[0]
        readiness = json.loads(run(["gh", "pr", "view", str(pr["number"]), "--repo", repo,
                                    "--json", "isDraft"], root).stdout)
        require(type(readiness.get("isDraft")) is bool, "Cannot resolve existing PR review readiness.")
        result["draft"] = draft or readiness["isDraft"]
        if draft and not readiness["isDraft"]:
            run(["gh", "pr", "ready", str(pr["number"]), "--repo", repo, "--undo"], root)
        # A passed gate does not silently publish an existing Draft for review.
    run(["git", "push", "--set-upstream", "origin", branch], root)
    if open_prs:
        run(["gh", "pr", "edit", str(pr["number"]), "--repo", repo,
             "--title", pr_title, "--body-file", str(Path(body_file).resolve())], root)
        result.update(status="updated", pr=pr["url"], number=pr["number"])
    else:
        command = ["gh", "pr", "create", "--repo", repo, "--base", base,
                   "--head", branch, "--title", pr_title, "--body-file", str(Path(body_file).resolve())]
        if draft:
            command.append("--draft")
        url = run(command, root).stdout.strip()
        require(re.fullmatch(r"https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[0-9]+", url), "GitHub returned an unexpected PR URL. Inspect existing PRs before retrying.")
        result.update(status="created", pr=url, number=int(url.rsplit("/", 1)[1]))
    result["plane_writeback"] = "pending: use Plane MCP for the delivery report; preserve task state for Draft PRs"
    return result


BINDING_MARKER = "<!-- plane-devflow "


def credential_guide(path, *, step="plane"):
    """Return non-secret browser guidance; verification reads Secret metadata only."""
    root, config = repo_config(path)
    if sync_provider(config) == "native":
        return {"status": "skipped", "provider": "native", "reason": "native_does_not_need_runner_pat"}
    require(step in {"plane", "github", "verify"}, "Choose plane, github or verify credential step.")
    repo = config["github"]["repository"]
    plane = config["plane"]
    result = {"provider": "actions", "repository": repo, "step": step,
              "secret_name": "PLANE_API_KEY", "writes_performed": False}
    if step == "plane":
        result.update(status="awaiting_user", url=plane["app_url"].rstrip("/") + "/" + quote(plane["workspace"], safe="") + "/",
                      navigation=["Open user menu", "Settings", "Personal Access Tokens", "Add access token"],
                      suggested_title="Plane DevFlow: " + repo,
                      suggested_description="GitHub Actions synchronization for " + repo,
                      expiry="User chooses an explicit expiry suitable for this automation.",
                      handoff="User generates and copies the PAT on Plane. Do not observe the generated value.",
                      next_step="github", advance_when="User confirms a PAT was created or already has a suitable PAT.")
    elif step == "github":
        result.update(status="awaiting_user", url="https://github.com/" + repo + "/settings/secrets/actions/new",
                      settings_url="https://github.com/" + repo + "/settings/secrets/actions",
                      navigation=["Settings", "Secrets and variables", "Actions", "New repository secret"],
                      name_field="PLANE_API_KEY",
                      handoff="User pastes the PAT into Secret and saves it on GitHub. No token in chat, screenshots, tool output or clipboard reads.",
                      next_step="verify", advance_when="User confirms the repository Secret was saved.")
    else:
        from setup_errors import github_json
        records = github_json(["gh", "secret", "list", "--repo", repo, "--json", "name,updatedAt"], root, "secret_metadata")
        require(isinstance(records, list) and all(isinstance(row, dict) for row in records),
                "GitHub returned invalid Secret metadata; cannot verify storage.")
        found = next((row for row in records if row.get("name") == "PLANE_API_KEY"), None)
        result.update(status="secret_present" if found is not None else "secret_missing",
                      secret_present=found is not None, secret_updated_at=found.get("updatedAt") if found is not None else None,
                      credential_value_read=False, next_step="activation" if found is not None else "github",
                      note="Secret presence is not proof of PAT validity or workflow connection. Continue check-github and trusted default-branch activation.")
    return result


def set_secret(path):
    _, config = repo_config(path)
    require(sync_provider(config) == "actions", "Native mode does not need a runner PAT Secret.")
    require(sys.stdin.isatty(), "Run set-secret directly in an interactive terminal, or use GitHub's repository Secrets page.")
    token = getpass.getpass("Plane PAT (hidden; sent only to GitHub repository Secret): ")
    require(bool(token.strip()), "No token supplied.")
    run(["gh", "secret", "set", "PLANE_API_KEY", "--repo", config["github"]["repository"]], input_text=token)
    return {"status": "stored", "secret": "PLANE_API_KEY", "repository": config["github"]["repository"]}


def demo(output=None):
    """Exercise real local Git and sync logic with isolated mock Plane data."""
    directory = Path(output).resolve() if output else Path(tempfile.mkdtemp(prefix="plane-devflow-demo-"))
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
    # This legacy offline fixture deliberately uses no network-backed preparation.
    start = _prepare_checkout(checkout, "DEMO-1", apply=True)
    resume = _prepare_checkout(checkout, "DEMO-1", apply=True)
    from checkout_workflow import context
    context(checkout, "DEMO-1", allowed_paths=["hello.txt"],
            expected=context(checkout, "DEMO-1")["context_sha256"], apply=True)
    (checkout / "hello.txt").write_text("Hello, Plane DevFlow\n")
    run(["git", "add", "hello.txt"], checkout)
    run(["git", "commit", "-m", "DEMO-1: update greeting"], checkout)
    from task_progress import progress, digest, report, check_task
    head = run(["git", "rev-parse", "HEAD"], checkout).stdout.strip()
    brief = {"goal": "Update the project greeting", "scope": ["hello.txt"], "out_of_scope": [],
             "scenarios": ["Read the updated greeting"],
             "criteria": [{"id": "greeting", "description": "Greeting contains the project name", "required": True, "stage": "review"}]}
    evidence = {"head": head, "brief_sha256": digest(brief), "evidence": "Read hello.txt in the isolated demo"}
    progress(checkout, "DEMO-1", update={"brief": brief,
             "design": {"required": False, "status": "not_required", "evidence": "Text-only demo", "brief_sha256": digest(brief)},
             "checks": [{**evidence, "id": "read-greeting", "criteria": ["greeting"], "kind": "test", "status": "passed"}],
             "self_review": {**evidence, "evidence": "Reviewed the isolated greeting diff"}}, expected="missing", apply=True)
    review_check = check_task(checkout, "DEMO-1", "review")
    body = report(checkout, "DEMO-1", "Add the project greeting.")
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
              "start": start, "resume": resume, "delivery": deliver, "review_check": review_check, "pr_open": opened,
              "pr_merged": merged, "repeat_merge": repeated, "manual_acceptance": manual,
              "lifecycle_comment_count": len(plane.comments), "report": str(report_path)}
    require(resume["operation"] == "resume" and review_check["ready"] and len(plane.comments) == 1 and manual["manual_acceptance"], "Demo invariant failed.")
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
    for key in ("workspace", "project-id", "project-key"):
        p.add_argument("--" + key, required=True)
    for key in ("in-progress", "in-review", "done"):
        p.add_argument("--" + key)
    p.add_argument("--base")
    p.add_argument("--branch-prefix")
    p.add_argument("--api-url", default="https://api.plane.so")
    p.add_argument("--app-url", default="https://app.plane.so")
    p.add_argument("--completion", choices=["on_merge", "manual"])
    p.add_argument("--action-source")
    p.add_argument("--sync-provider", choices=["actions", "native"])
    p.add_argument("--api-version", choices=["v1", "v2"])
    p.add_argument("--replace", action="store_true")
    p.add_argument("--expected-config-sha256")
    p.add_argument("--disable-state-sync", action="store_true")
    p.add_argument("--project-file")
    p.add_argument("--workspace-file")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("project-options", help="Present MCP projects for user selection; never auto-bind a recommendation.")
    p.add_argument("--repo", default=".")
    p.add_argument("--projects-file", required=True)
    p.add_argument("--workspace-file", required=True)
    p = sub.add_parser("prepare", help="Plan or prepare a task branch/worktree.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--worktree")
    p.add_argument("--in-place", action="store_true", help="Explicitly prepare in the caller checkout, e.g. a fresh Codex-managed worktree.")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("render-report", help="Create a linked PR body from observed results.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--summary-file", required=True)
    p.add_argument("--checks-file")
    p.add_argument("--from-progress", action="store_true", help="Render current task receipt instead of free-text checks/acceptance.")
    p.add_argument("--stage", choices=["review", "merge", "complete"], default="review")
    p.add_argument("--workitem-file", help="Fresh normalized Plane MCP task snapshot for completion checks.")
    p.add_argument("--remaining-file")
    p.add_argument("--output", required=True)
    p = sub.add_parser("deliver", help="Plan or push and create/update a PR; Plane writeback uses MCP.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--draft", action="store_true", help="Deliver incomplete work without declaring it ready for acceptance.")
    p = sub.add_parser("task-progress", help="Inspect or plan/apply a task receipt in shared Git metadata.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--record-file")
    p.add_argument("--expected-record-sha256")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("task-context", help="Check task checkout/scope or plan/apply its authorized file scope.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--scope-file", help="JSON array of authorized repository-relative paths/glob patterns.")
    p.add_argument("--expected-context-sha256")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("write-context", help="Read-only task routing before any repository write, including plans/research.")
    p.add_argument("task", nargs="?")
    p.add_argument("--repo", default=".")
    p.add_argument("--mode", choices=["discussion", "write"], required=True)
    p.add_argument("--path", action="append", default=[], help="Concrete repository-relative file to write; repeat for multiple files.")
    p = sub.add_parser("sync-task", help="Plan or merge the latest configured base into this task; preserve conflicts for resolution.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("finish-task", help="After confirmed task completion, update the primary checkout to the configured base.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--workitem-file", required=True, help="Fresh completed Plane task snapshot after readback.")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("check-task", help="Check implementation, review, merge or completion evidence; no writes.")
    p.add_argument("task")
    p.add_argument("--repo", default=".")
    p.add_argument("--stage", choices=["implement", "review", "merge", "complete"], required=True)
    p.add_argument("--workitem-file", help="Fresh normalized Plane MCP task snapshot for completion checks.")
    p = sub.add_parser("credential-guide", help="Guide Plane PAT creation, GitHub storage, and metadata-only verification.")
    p.add_argument("--repo", default=".")
    p.add_argument("--step", choices=["plane", "github", "verify"], default="plane")
    p = sub.add_parser("setup-progress", help="Inspect capabilities, resume setup and optionally save non-secret progress in Git metadata.")
    p.add_argument("--repo", default=".")
    p.add_argument("--offline", action="store_true", help="Leave remote checks unknown; never reuse cached success as current evidence.")
    p.add_argument("--surface", action="append", choices=["browser-control", "app-control", "url-opener"], default=[],
                   help="Report only tools actually available in this host; defaults to manual links.")
    p.add_argument("--event", choices=["pat-ready", "pat-unavailable", "secret-saved"])
    p.add_argument("--apply", action="store_true", help="Persist non-secret progress; no external writes.")
    p = sub.add_parser("setup-capabilities", help="Inspect local prerequisites and reported host surfaces without a repository or account.")
    p.add_argument("--surface", action="append", choices=["browser-control", "app-control", "url-opener"], default=[])
    p = sub.add_parser("set-secret", help="Read a Plane PAT through hidden terminal input and store it in GitHub.")
    p.add_argument("--repo", default=".")
    p = sub.add_parser("setup-github", help="Prepare bundled PR synchronization and a read-only connection check.")
    p.add_argument("--repo", default=".")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--upgrade", action="store_true")
    p.add_argument("--expected-files-sha256")
    p = sub.add_parser("check-github", help="Check remote setup readiness; Secret values are never read.")
    p.add_argument("--repo", default=".")
    p.add_argument("--native-evidence-file")
    p = sub.add_parser("record-native", help="Record observed official integration mapping; no automatic discovery claim.")
    p.add_argument("--repo", default=".")
    p.add_argument("--evidence-file", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("demo", help="Run an isolated end-to-end offline demo; no accounts needed.")
    p.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.repo)
        elif args.command == "configure":
            result = configure(args)
        elif args.command == "project-options":
            result = project_options(args.repo, args.projects_file, args.workspace_file)
        elif args.command == "prepare":
            result = prepare(args.repo, args.task, worktree=args.worktree, in_place=args.in_place, apply=args.apply)
        elif args.command == "render-report":
            if args.from_progress:
                from task_progress import report
                text = report(args.repo, args.task, Path(args.summary_file).read_text(), stage=args.stage,
                              workitem=json.loads(Path(args.workitem_file).read_text()) if args.workitem_file else None)
            else:
                require(args.checks_file is not None, "Supply --checks-file or use --from-progress.")
                text = render_report(args.repo, args.task, Path(args.summary_file).read_text(), Path(args.checks_file).read_text(),
                                     Path(args.remaining_file).read_text() if args.remaining_file else "")
            output = Path(args.output)
            require(not output.exists(), "Report output already exists. Choose another path or edit it explicitly.")
            output.write_text(text)
            result = {"status": "written", "output": str(output.resolve()), "sha256": hashlib.sha256(text.encode()).hexdigest()}
        elif args.command == "deliver":
            result = delivery(args.repo, args.task, args.title, args.body_file, apply=args.apply, draft=args.draft)
        elif args.command == "task-progress":
            from task_progress import progress
            result = progress(args.repo, args.task, update=json.loads(Path(args.record_file).read_text()) if args.record_file else None,
                              expected=args.expected_record_sha256, apply=args.apply)
        elif args.command == "task-context":
            from checkout_workflow import context
            result = context(args.repo, args.task,
                             allowed_paths=json.loads(Path(args.scope_file).read_text()) if args.scope_file else None,
                             expected=args.expected_context_sha256, apply=args.apply)
        elif args.command == "write-context":
            from checkout_workflow import write_context
            result = write_context(args.repo, args.task, mode=args.mode, planned_paths=args.path)
        elif args.command == "sync-task":
            from task_workspaces import sync_task
            result = sync_task(args.repo, args.task, apply=args.apply)
        elif args.command == "finish-task":
            from checkout_workflow import finish
            result = finish(args.repo, args.task, workitem=json.loads(Path(args.workitem_file).read_text()), apply=args.apply)
        elif args.command == "check-task":
            from task_progress import check_task
            result = check_task(args.repo, args.task, args.stage,
                                workitem=json.loads(Path(args.workitem_file).read_text()) if args.workitem_file else None)
        elif args.command == "credential-guide":
            result = credential_guide(args.repo, step=args.step)
        elif args.command == "setup-progress":
            from onboarding import progress
            result = progress(args.repo, surfaces=args.surface, offline=args.offline, event=args.event, apply=args.apply)
        elif args.command == "setup-capabilities":
            from onboarding import capabilities
            result = capabilities(args.surface)
        elif args.command == "set-secret":
            result = set_secret(args.repo)
        elif args.command == "setup-github":
            from github_setup import install
            result = install(args.repo, apply=args.apply, upgrade=args.upgrade, expected_files_sha256=args.expected_files_sha256)
        elif args.command == "check-github":
            from github_setup import check
            result = check(args.repo, native_evidence_file=args.native_evidence_file)
        elif args.command == "record-native":
            from github_setup import record_native
            result = record_native(args.repo, args.evidence_file, apply=args.apply)
        else:
            result = demo(args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.command in {"check-task", "finish-task", "task-context", "write-context", "sync-task"} and result.get("ready") is False else 0
    except (WorkflowError, OSError, ValueError, TypeError) as error:
        print(f"plane-devflow: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
