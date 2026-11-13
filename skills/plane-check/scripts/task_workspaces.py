"""Select isolated task workspaces without switching another chat's checkout."""
from __future__ import annotations

from contextlib import contextmanager
import os
import time
from pathlib import Path

from plane_sync import parse_task, require


@contextmanager
def workspace_lock(root, task_identity=None):
    from plane_workflow import run
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    from task_progress import digest
    name = "workspaces" if task_identity is None else "sync-" + digest(task_identity)
    path = common / ("plane-devflow-" + name + ".lock")
    require(not path.is_symlink(), "Workspace lock must not be a symlink.")
    deadline = time.monotonic() + 35
    while True:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            break
        except FileExistsError:
            require(time.monotonic() < deadline,
                    "Another workspace operation is running. Retry after it finishes; preserve its lock.")
            time.sleep(0.05)
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def selected_workspace(root, config, task, requested=None, *, agent=None):
    from checkout_workflow import metadata_path, read_metadata, worktrees
    from task_progress import identity
    from plane_workflow import repo_config, run, branch_name, same_task_mapping
    trees = worktrees(root)
    require(trees and "bare" not in trees[0], "Cannot identify the primary checkout.")
    primary = Path(trees[0]["worktree"]).resolve()
    branch = branch_name(task, config, root=root, agent=agent)
    record, _ = read_metadata(metadata_path(root, config, task, "checkouts"), identity(config, task))
    owners = [Path(t["worktree"]).resolve() for t in trees if t.get("branch") == "refs/heads/" + branch]
    target = Path(requested).expanduser().resolve() if requested else None
    if record:
        bound = Path(record["checkout"]["path"])
        require(target is None or target == bound, "Task already has a bound checkout. Resume it instead of relocating it.")
        target = bound
        require(target.is_dir(), "Task checkout is missing. Preserve its record and recover the original workspace.")
        require(owners == [target], "Task branch ownership changed. Inspect its bound checkout before recovery.")
    elif owners:
        require(len(owners) == 1 and (target is None or target == owners[0]),
                "Task branch is already checked out elsewhere. Resume that workspace.")
        target = owners[0]
    elif target is None:
        target = primary.parent / (primary.name + "-plane-worktrees") / task.lower()
        require(not target.is_relative_to(primary), "Task workspaces must be outside the primary checkout.")
    if target.exists():
        actual_root, actual_config = repo_config(target)
        common = lambda p: run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], p).stdout.strip()
        require(actual_root == target and same_task_mapping(actual_config, config) and common(target) == common(root),
                "Selected workspace does not belong to this repository and Plane mapping.")
    return target, primary


def prepare_workspace(path, task, *, worktree=None, agent=None, apply=False):
    from plane_workflow import repo_config, run, _prepare_checkout
    root, config = repo_config(path)
    key = parse_task(task, config)
    target, primary = selected_workspace(root, config, key, worktree, agent=agent)
    if apply:
        base = config["github"]["base_branch"]
        with workspace_lock(root):
            run(["git", "fetch", "origin", f"refs/heads/{base}:refs/remotes/origin/{base}"], root)
            require(repo_config(root)[1] == config, "Repository mapping changed during workspace preparation.")
            target, primary = selected_workspace(root, config, key, worktree, agent=agent)
            result = _prepare_checkout(root, key, worktree=target, agent=agent, apply=True)
    else:
        result = _prepare_checkout(root, key, worktree=target, agent=agent)
    result.update(caller_path=str(root), primary_path=str(primary), execution_path=str(target),
                  isolated=target != primary, base_freshness="fetched" if apply else "unverified")
    return result


def sync_task(path, task, *, apply=False):
    """Merge the configured base into this task only; conflicts remain for scoped resolution."""
    from checkout_workflow import inspect, merge_state, base_ref
    from plane_workflow import repo_config, run
    from task_progress import identity
    root, config = repo_config(path)
    key = parse_task(task, config)
    before = inspect(root, config, key)
    result = {"task": key, "path": str(root), "base": config["github"]["base_branch"],
              "ready": False, "status": "planned", "blockers": list(before["blockers"]),
              "previous_head": before["head"], "base_freshness": "unverified"}

    def pending(state):
        result.update(status="conflicts" if state["conflicted_paths"] else "merge_in_progress",
                      integration=state, conflicted_paths=state["conflicted_paths"],
                      next_action="resolve_stage_and_commit_base_merge" if state["is_base_merge"] else "inspect_existing_git_operation")
        result["blockers"].append("base_merge_in_progress" if state["is_base_merge"] else "unrelated_git_operation_in_progress")
        return result

    if result["blockers"]:
        result["status"] = "blocked"
        return result
    state = merge_state(root, config)
    if state["operations"]:
        return pending(state)
    require(not run(["git", "status", "--porcelain"], root).stdout.strip(),
            "Commit intended task changes before merging the base; preserve uncommitted work.")
    if apply:
        base = config["github"]["base_branch"]
        run(["git", "fetch", "origin", f"refs/heads/{base}:refs/remotes/origin/{base}"], root)
        result["base_freshness"] = "fetched"
    ref = base_ref(root, config)
    result["base_sha"] = run(["git", "rev-parse", ref], root).stdout.strip()
    result["update_required"] = run(["git", "merge-base", "--is-ancestor", ref, "HEAD"], root, check=False).returncode != 0
    if not apply:
        result["ready"] = True
        return result
    with workspace_lock(root, identity(config, key)):
        current = inspect(root, config, key)
        require(repo_config(root)[1] == config and current["ready"] and
                current["head"] == before["head"] and current["context_sha256"] == before["context_sha256"] and
                not merge_state(root, config)["operations"] and
                not run(["git", "status", "--porcelain"], root).stdout.strip(),
                "Task checkout, scope or changes moved during fetch. Inspect before merging its base.")
        if result["update_required"]:
            merged = run(["git", "-c", "merge.autoStash=false", "merge", "--no-edit", "--no-ff", result["base_sha"]], root, check=False)
            if merged.returncode:
                state = merge_state(root, config)
                if state["operations"]:
                    return pending(state)
                require(False, "Base merge failed. Inspect this task checkout before retrying.")
        after = inspect(root, config, key)
        result.update(head=after["head"], needs_reverification=after["head"] != before["head"],
                      ready=after["ready"], blockers=after["blockers"],
                      status="updated" if result["update_required"] else "up_to_date")
    return result
