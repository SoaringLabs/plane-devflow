"""Task checkout/scope checks and post-completion base checkout handoff."""
from __future__ import annotations

import fnmatch
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from plane_sync import WorkflowError, require
from task_progress import SHA, digest, identity


def metadata_path(root, config, task, kind):
    from plane_workflow import run
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    path = common / "plane-for-codex" / kind / (digest(identity(config, task)) + ".json")
    require(not any(p.is_symlink() for p in (path, path.parent, path.parent.parent)),
            "Checkout metadata must not resolve through symlinks.")
    return path


def read_metadata(path, task_identity):
    if not path.exists():
        return None, "missing"
    raw = path.read_bytes()
    try:
        record = json.loads(raw)
        require(record["version"] == 1 and record["identity"] == task_identity, "Wrong checkout record identity.")
        if path.parent.name == "checkouts":
            validate_checkout(record["checkout"])
    except (ValueError, KeyError, TypeError):
        raise WorkflowError("Checkout record is invalid. Preserve it and inspect before recovery.") from None
    return record, hashlib.sha256(raw).hexdigest()


def validate_checkout(value):
    from task_progress import fields, strings
    fields(value, {"path", "branch", "base_sha", "allowed_paths"}, {"path", "branch", "base_sha", "allowed_paths"})
    require(isinstance(value["path"], str) and Path(value["path"]).is_absolute() and
            isinstance(value["branch"], str) and SHA.fullmatch(value["base_sha"]) is not None,
            "Invalid checkout directory, branch or base commit.")
    strings(value["allowed_paths"])
    for pattern in value["allowed_paths"]:
        require(not pattern.startswith("/") and ".." not in PurePosixPath(pattern).parts and
                "\\" not in pattern and "\0" not in pattern and pattern not in {".", ""},
                "Scope paths must be repository-relative paths or glob patterns.")


def base_ref(root, config):
    from plane_workflow import run
    base = config["github"]["base_branch"]
    remote = "refs/remotes/origin/" + base
    return remote if run(["git", "rev-parse", "--verify", remote], root, check=False).returncode == 0 else "refs/heads/" + base


def capture(root, config, task, *, base_sha=None, allowed_paths=None, expected=None, apply=False):
    """Plan/apply a checkout binding. Existing scope/base stay intact on resume."""
    from plane_workflow import branch_name, run, configuration_lock, atomic_write, repo_config, repo_root
    root = repo_root(root)
    destination = metadata_path(root, config, task, "checkouts")
    previous, before = read_metadata(destination, identity(config, task))
    branch = branch_name(task, config)
    require(run(["git", "branch", "--show-current"], root).stdout.strip() == branch,
            "Switch to the selected task branch before recording its checkout.")
    if previous:
        validate_checkout(previous["checkout"])
        require(previous["checkout"]["path"] == str(root) and previous["checkout"]["branch"] == branch,
                "Task checkout changed. Inspect the original directory and task branch before rebinding.")
    checkout = previous["checkout"].copy() if previous else {
        "path": str(root), "branch": branch,
        "base_sha": base_sha or run(["git", "merge-base", "HEAD", base_ref(root, config)], root).stdout.strip(),
        "allowed_paths": []}
    if allowed_paths is not None:
        require(bool(allowed_paths), "Record the authorized file scope before implementation.")
        checkout["allowed_paths"] = allowed_paths
    validate_checkout(checkout)
    record = {"version": 1, "identity": identity(config, task), "checkout": checkout}
    result = {"status": "planned", "expected_context_sha256": before, "record": record}
    if apply:
        require(expected == before, "Apply with the inspected --expected-context-sha256.")
        with configuration_lock(root):
            require(repo_config(root)[1] == config and
                    run(["git", "branch", "--show-current"], root).stdout.strip() == branch,
                    "Mapping or task branch changed while recording its checkout.")
            require(read_metadata(destination, identity(config, task))[1] == before,
                    "Checkout record changed concurrently; inspect again.")
            metadata_path(root, config, task, "checkouts")
            destination.parent.mkdir(exist_ok=True)
            if record != previous:
                atomic_write(destination, (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
        result.update(status="recorded", context_sha256=read_metadata(destination, identity(config, task))[1])
    return result


def inspect(root, config, task):
    from plane_workflow import branch_name, run
    record, stamp = read_metadata(metadata_path(root, config, task, "checkouts"), identity(config, task))
    current_branch = run(["git", "branch", "--show-current"], root).stdout.strip()
    head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
    result = {"ready": False, "blockers": [], "path": str(root), "branch": current_branch, "head": head,
              "context_sha256": stamp, "changed_paths": [], "outside_scope": []}
    blockers = result["blockers"]
    if current_branch != branch_name(task, config):
        blockers.append("task_branch_mismatch")
    if not record:
        blockers.append("task_checkout_missing")
        return result
    checkout = record["checkout"]
    validate_checkout(checkout)
    result["checkout"] = checkout
    if checkout["path"] != str(root) or checkout["branch"] != branch_name(task, config):
        blockers.append("task_checkout_mismatch")
    if not checkout["allowed_paths"]:
        blockers.append("task_file_scope_missing")
    baseline = checkout["base_sha"]
    if run(["git", "merge-base", "--is-ancestor", baseline, head], root, check=False).returncode:
        blockers.append("task_base_history_changed")
    else:
        paths = set()
        committed = set(filter(None, run(["git", "diff", "--name-only", "--no-renames", "-z", baseline, "HEAD", "--"], root).stdout.split("\0")))
        # --no-renames accounts for both source and destination paths of a rename.
        for args in (["diff", "--name-only", "--no-renames", "-z", baseline, "HEAD", "--"],
                     ["diff", "--name-only", "--no-renames", "-z", "HEAD", "--"],
                     ["diff", "--name-only", "--no-renames", "-z", "--cached", "--"],
                     ["ls-files", "--others", "--exclude-standard", "-z"]):
            paths.update(filter(None, run(["git", *args], root).stdout.split("\0")))
        result["changed_paths"] = sorted(paths)
        result["outside_scope"] = sorted(p for p in paths if not any(
            fnmatch.fnmatchcase(p, pattern) for pattern in checkout["allowed_paths"]))
        if result["outside_scope"]:
            blockers.append("changes_outside_task_scope")
        if head != baseline:
            base = base_ref(root, config)
            integrated = run(["git", "merge-base", "--is-ancestor", head, base], root, check=False).returncode == 0
            # A squash has a different SHA; compare the task's changed paths as well.
            same_content = bool(committed) and run(["git", "diff", "--quiet", base, "HEAD", "--", *sorted(committed)],
                                                  root, check=False).returncode == 0
            if integrated or same_content:
                blockers.append("task_head_already_in_base")
    result["ready"] = not blockers
    return result


def context(path, task, *, allowed_paths=None, expected=None, apply=False):
    from plane_workflow import repo_config
    root, config = repo_config(path)
    if allowed_paths is not None:
        return capture(root, config, task, allowed_paths=allowed_paths, expected=expected, apply=apply)
    require(not apply, "Supply --scope-file when applying task-context.")
    return inspect(root, config, task)


def worktrees(root):
    from plane_workflow import run
    records = run(["git", "worktree", "list", "--porcelain", "-z"], root).stdout.split("\0\0")
    return [dict(field.split(" ", 1) if " " in field else (field, "")
                 for field in record.split("\0") if field) for record in records if record.strip("\0")]


def handoff_target(root, config, task):
    from plane_workflow import repo_config, branch_name, run
    trees = worktrees(root)
    require(trees and "bare" not in trees[0], "Cannot identify the primary checkout.")
    primary = Path(trees[0]["worktree"]).resolve()
    require(repo_config(primary)[1] == config, "Primary checkout has a different repository mapping.")
    base = config["github"]["base_branch"]
    owners = [t for t in trees if t.get("branch") == "refs/heads/" + base]
    require(not owners or Path(owners[0]["worktree"]).resolve() == primary,
            "Base branch is checked out in another worktree. Preserve it and resolve its ownership.")
    for directory in {root, primary}:
        require(not run(["git", "status", "--porcelain"], directory).stdout.strip(),
                "Checkout has uncommitted changes. Preserve them before the base handoff.")
        branch = run(["git", "branch", "--show-current"], directory).stdout.strip()
        require(branch in {base, branch_name(task, config)},
                "Checkout belongs to another task or detached HEAD. Preserve its branch.")
        for operation in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"):
            marker = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-path", operation], directory).stdout.strip())
            require(not marker.exists(), "A Git operation is in progress. Finish it before the base handoff.")
    return primary


def finish(path, task, *, workitem, apply=False):
    """The Skill calls this only after authorized finalization and Plane readback."""
    from plane_workflow import repo_config, run, configuration_lock, atomic_write
    from task_progress import check_task, progress
    root, config = repo_config(path)
    task_identity = identity(config, task)
    destination = metadata_path(root, config, task, "handoffs")
    previous, _ = read_metadata(destination, task_identity)
    gate = check_task(root, task, "complete", workitem=workitem)
    result = {"status": "planned", "ready": False, "task": task_identity["task"],
              "base": config["github"]["base_branch"], "completion_check": gate,
              "previous_handoff": previous, "phase": "completion_check", "blockers": list(gate["blockers"])}
    if not workitem or workitem.get("state_group") != "completed":
        result["blockers"].append("task_completion_not_confirmed")
    if result["blockers"]:
        result["status"] = "pending" if apply else "blocked"
        return result
    merge = gate["pr"]["mergeCommit"]["oid"]
    require(SHA.fullmatch(merge) is not None, "Invalid merged commit.")
    result["merge_commit"] = merge

    def preflight():
        target = handoff_target(root, config, task)
        require(progress(root, task)["record_sha256"] == gate["record_sha256"],
                "Task evidence changed; recheck completion before handoff.")
        return target

    try:
        result["phase"] = "checkout_preflight"
        target = preflight()
        result["path"] = str(target)
        result["ready"] = True
        if not apply:
            return result
        with configuration_lock(root):
            def persist():
                metadata_path(root, config, task, "handoffs")
                destination.parent.mkdir(exist_ok=True)
                # Keep completion receipts unchanged; this checkpoint only tracks local handoff.
                saved = {k: v for k, v in result.items() if k not in {"completion_check", "previous_handoff"}}
                saved.update(version=1, identity=task_identity, observed_at=datetime.now(timezone.utc).isoformat())
                atomic_write(destination, (json.dumps(saved, ensure_ascii=False, indent=2) + "\n").encode())

            result.update(status="pending", ready=False)
            persist()
            try:
                target = preflight()
                initial_branch = run(["git", "branch", "--show-current"], target).stdout.strip()
                initial_head = run(["git", "rev-parse", "HEAD"], target).stdout.strip()
                base = config["github"]["base_branch"]
                remote = "refs/remotes/origin/" + base
                result["phase"] = "fetch"
                run(["git", "fetch", "origin", f"refs/heads/{base}:{remote}"], target)
                remote_head = run(["git", "rev-parse", remote], target).stdout.strip()
                require(run(["git", "merge-base", "--is-ancestor", merge, remote_head], target, check=False).returncode == 0,
                        "Refreshed base does not contain the merged PR commit.")
                local_ref = "refs/heads/" + base
                exists = run(["git", "show-ref", "--verify", "--quiet", local_ref], target, check=False).returncode == 0
                if exists:
                    require(run(["git", "merge-base", "--is-ancestor", local_ref, remote], target, check=False).returncode == 0,
                            "Local base has unique commits or diverges. Preserve it; automatic handoff stopped.")
                require(preflight() == target and run(["git", "rev-parse", "HEAD"], target).stdout.strip() == initial_head and
                        run(["git", "branch", "--show-current"], target).stdout.strip() == initial_branch,
                        "Checkout changed during fetch. Inspect before switching.")
                result["phase"] = "switch"
                run(["git", "switch", base] if exists else ["git", "switch", "--create", base, "--track", "origin/" + base], target)
                require(preflight() == target and run(["git", "branch", "--show-current"], target).stdout.strip() == base,
                        "Checkout changed before pull. Preserve it and inspect.")
                result["phase"] = "pull"
                # Explicit remote/ref avoids relying on a task branch's tracking configuration.
                run(["git", "-c", "pull.rebase=false", "pull", "--ff-only", "origin", base], target)
                result["phase"] = "verify"
                head = run(["git", "rev-parse", "HEAD"], target).stdout.strip()
                remote_head = run(["git", "rev-parse", remote], target).stdout.strip()
                require(preflight() == target and run(["git", "branch", "--show-current"], target).stdout.strip() == base and
                        head == remote_head and run(["git", "merge-base", "--is-ancestor", merge, head], target, check=False).returncode == 0,
                        "Base checkout parity or merged content is unverified. Inspect before starting another task.")
                result.update(status="ready", ready=True, head=head, remote_head=remote_head, blockers=[])
            except (WorkflowError, OSError, ValueError) as error:
                result.update(status="pending", ready=False, blockers=[str(error)])
            persist()
    except (WorkflowError, OSError, ValueError) as error:
        result.update(status="pending" if apply else "blocked", ready=False, blockers=[str(error)])
        if apply:
            # Preflight failures also remain resumable, without altering task completion.
            try:
                with configuration_lock(root):
                    metadata_path(root, config, task, "handoffs")
                    destination.parent.mkdir(exist_ok=True)
                    saved = {k: v for k, v in result.items() if k not in {"completion_check", "previous_handoff"}}
                    saved.update(version=1, identity=task_identity, observed_at=datetime.now(timezone.utc).isoformat())
                    atomic_write(destination, (json.dumps(saved, ensure_ascii=False, indent=2) + "\n").encode())
            except (WorkflowError, OSError):
                result["limitations"] = ["handoff_checkpoint_not_saved; preserve existing metadata and inspect before retrying"]
    return result
