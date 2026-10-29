"""Read-only task reconciliation. No fetch, cache writes, dispatch or remote mutation."""
from datetime import datetime, timezone
from pathlib import Path

from plane_sync import WorkflowError, parse_task, require
from task_progress import digest, gates, identity, progress, strings


def plane_snapshot(value, config, task, now):
    """The host supplies MCP observations; this helper has no Plane credentials."""
    try:
        require(isinstance(value, dict) and set(value) ==
                {"task", "project_id", "labels", "state_group", "observed_at"}, "Missing task snapshot.")
        require(value["task"] == task and value["project_id"] == config["plane"]["project_id"],
                "Task snapshot identity mismatch.")
        strings(value["labels"])
        require(isinstance(value["state_group"], str) and bool(value["state_group"]), "Missing task state group.")
        observed = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
        require(observed.tzinfo is not None and 0 <= (now - observed).total_seconds() <= 300,
                "Task snapshot is stale or has a future timestamp.")
        return {"status": "observed", "source": "host_mcp_snapshot", **value}
    except (WorkflowError, TypeError, ValueError, KeyError, AttributeError) as error:
        return {"status": "unknown", "source": "host_mcp_snapshot", "reason": str(error)}


def status(path, task, *, refresh=False, workitem=None):
    from plane_workflow import repo_config, run, doctor, same_task_mapping
    from checkout_workflow import inspect, metadata_path, read_metadata, worktrees, merge_state
    from sync_health import status as sync_status
    from task_progress import check_task

    root, config = repo_config(path)
    task = parse_task(task, config)
    now = datetime.now(timezone.utc)
    observed = now.isoformat()
    blockers, limitations = [], []
    result = {"task": task, "observed_at": observed, "read_only": True,
              "mode": "explicit_refresh" if refresh else "local_and_cache",
              "authority": "Receipts are declarations. Verify original human messages before acceptance or merge; this diagnosis grants no authority.",
              "blockers": blockers, "limitations": limitations}
    result["caller"] = {"path": str(root), "branch": run(["git", "branch", "--show-current"], root).stdout.strip(),
                        "head": run(["git", "rev-parse", "HEAD"], root).stdout.strip()}
    execution = root
    binding = None
    try:
        binding, _ = read_metadata(metadata_path(root, config, task, "checkouts"), identity(config, task))
        if binding:
            target = Path(binding["checkout"]["path"]).resolve()
            registered = {Path(t["worktree"]).resolve() for t in worktrees(root) if "worktree" in t}
            require(target in registered and same_task_mapping(repo_config(target)[1], config),
                    "Recorded task directory is unavailable or has a different mapping; preserve it and inspect.")
            execution = target
        context = inspect(execution, config, task)
        result["checkout"] = {"source": "local_git_and_binding", "observed_at": observed, **context}
        blockers.extend(context["blockers"])
        result["checkout"]["git_operations"] = merge_state(execution, config)
        if result["checkout"]["git_operations"]["operations"]:
            blockers.append("task_git_operation_in_progress")
        if run(["git", "status", "--porcelain"], execution).stdout.strip():
            blockers.append("uncommitted_changes_not_covered")
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as error:
        result["checkout"] = {"status": "unknown", "reason": str(error), "source": "local_git_and_binding"}
        blockers.append("task_checkout_unverified")
    result["execution_path"] = str(execution)
    result["caller_is_execution_path"] = root == execution
    local_head = run(["git", "rev-parse", "HEAD"], execution).stdout.strip()
    try:
        receipt = progress(root, task)
        record = receipt["record"] or {}
        data = record.get("data", {})
        result["receipt"] = {"status": receipt["status"], "source": "local_declaration",
                             "updated_at": record.get("updated_at"), "sha256": receipt["record_sha256"]}
    except (WorkflowError, OSError, ValueError) as error:
        data = {}
        result["receipt"] = {"status": "unknown", "source": "local_declaration", "reason": str(error)}
        blockers.append("task_receipt_unverified")
    result["plane"] = plane_snapshot(workitem, config, task, now)
    if result["plane"]["status"] != "observed":
        limitations.append("live_plane_task_unverified")
    result["github"] = {"status": "unknown", "source": "not_requested", "pr": None, "required_checks": None,
                        "reason": "Use explicit --refresh for current PR/CI reads; no routine remote request is made."}
    evidence_head = local_head
    if refresh:
        try:
            live = check_task(execution, task, "complete", workitem=workitem)
            pr = live["pr"]
            valid = pr is not None and "live_pr_or_checks_unverified" not in live["blockers"]
            result["github"] = {"status": "observed" if valid else "unknown", "source": "explicit_gh_read",
                                "observed_at": observed, "required_checks": live["required_checks"] if valid else None,
                                "blockers": [b for b in live["blockers"] if b in {
                                    "live_pr_or_checks_unverified", "required_github_checks_not_passed", "primary_pr_missing"}],
                                "pr": {k: pr.get(k) for k in ("url", "state", "isDraft", "headRefOid", "baseRefName", "mergeCommit")} if valid else None}
            if valid:
                blockers.extend(b for b in live["blockers"] if b in {
                    "required_github_checks_not_passed", "pr_not_merged", "cancelled_task_preserved"})
                evidence_head = pr["headRefOid"]
                if evidence_head != local_head:
                    limitations.append("local_pr_head_mismatch")
            else:
                limitations.append("live_pr_or_checks_unverified")
        except (WorkflowError, OSError, ValueError, KeyError, TypeError) as error:
            result["github"].update(source="explicit_gh_read", reason=str(error))
            limitations.append("live_pr_or_checks_unverified")
    else:
        limitations.append("live_pr_or_checks_unverified")
    brief = data.get("brief", {})
    brief_hash = digest(brief)
    def freshness(value):
        if not value:
            return "missing"
        return "current_declaration" if value.get("head") == evidence_head and value.get("brief_sha256") == brief_hash else "stale"
    result["requirements"] = {"status": "recorded" if brief else "missing", "source": "local_declaration",
                              "brief_sha256": brief_hash, "criteria": brief.get("criteria", [])}
    result["verification"] = {"head": evidence_head, "source": "local_declaration",
                              "self_review": freshness(data.get("self_review")),
                              "checks": [{"id": c["id"], "kind": c["kind"], "declared_status": c["status"],
                                          "freshness": freshness(c), "criteria": c["criteria"]} for c in data.get("checks", [])]}
    for section in ("acceptance", "merge_authorization"):
        declaration = data.get(section)
        result[section] = {"status": freshness(declaration), "source": "local_declaration",
                           "human_message_verified": False,
                           "criteria": declaration.get("criteria", []) if declaration else []}
    manual = config["completion"]["policy"] == "manual" or result["plane"].get("status") != "observed" or config["completion"].get("manual_label", "manual-acceptance") in result["plane"].get("labels", [])
    result["local_gates"] = {stage: gates(data, evidence_head, stage, manual=manual) for stage in ("implement", "review", "merge", "complete")}
    blockers.extend(result["local_gates"]["complete"]["blockers"])
    blockers.extend(result["local_gates"]["merge"]["blockers"])
    limitations.extend(result["local_gates"]["complete"]["limitations"])
    delivery = data.get("delivery", {})
    result["writeback"] = {"status": delivery.get("plane_writeback", "missing"), "source": "local_declaration",
                           "head_matches": delivery.get("head") == evidence_head, "pr_url": delivery.get("pr_url"),
                           "current_remote_readback": False}
    result["environment"] = {"source": "local_declaration", "resources": [
        {k: r[k] for k in ("name", "owner", "disposition")} for r in data.get("environment", [])],
        "process_liveness_verified": False}
    try:
        handoff, _ = read_metadata(metadata_path(root, config, task, "handoffs"), identity(config, task))
        result["handoff"] = {"source": "local_checkpoint", "status": handoff.get("status") if handoff else "missing",
                             "observed_at": handoff.get("observed_at") if handoff else None,
                             "phase": handoff.get("phase") if handoff else None,
                             "current_base_parity_verified": False}
        if not handoff or handoff.get("status") != "ready":
            limitations.append("local_handoff_pending")
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as error:
        result["handoff"] = {"status": "unknown", "source": "local_checkpoint", "reason": str(error)}
        limitations.append("local_handoff_unverified")
    try:
        result["sync"] = sync_status(root, offline=not refresh, refresh=refresh, persist=False)
    except (WorkflowError, OSError, ValueError) as error:
        result["sync"] = {"status": "unknown", "reason": str(error)}
        limitations.append("sync_health_unverified")
    result["tools"] = doctor(root, offline=True)
    sync = result["sync"]
    observation = sync.get("observation", {})
    event_observed = sync.get("event_run_observed") is True
    result["actions_event"] = {
        "status": "repository_event_observed" if event_observed else "unknown",
        "source": observation.get("source", "not_observed"), "observed_at": observation.get("probed_at"),
        "task_binding_verified": False, "task_writeback_verified": False,
        "reason": "Repository workflow metadata can show an event run; inspect the actual task-bound event and Plane readback separately."}
    result["blockers"] = sorted(set(blockers))
    result["limitations"] = sorted(set(limitations))
    result["next_actions"] = []
    if result["blockers"]:
        result["next_actions"].append("Inspect the named blockers in the selected task directory; this command performs no repair.")
    if any("stale" in b or b.startswith("criterion_unverified:") for b in result["blockers"]):
        result["next_actions"].append("Recheck affected criteria at the current head/brief; preserve failed and unrun results.")
    if result["writeback"]["status"] == "pending":
        result["next_actions"].append("Read back the existing PR and Plane links/comments; resume only the missing authorized writeback.")
    if "agent_environment_cleanup_pending" in result["blockers"]:
        result["next_actions"].append("Verify ownership before cleaning or handing off the recorded agent resources.")
    if "local_handoff_pending" in result["limitations"]:
        result["next_actions"].append("After confirmed completion, inspect finish-task's plan before the authorized local handoff.")
    if result["plane"]["status"] != "observed":
        result["next_actions"].append("Read the explicit task through host Plane MCP and supply a fresh normalized --workitem-file.")
    if result["github"]["status"] != "observed":
        result["next_actions"].append("When current PR/CI facts are needed, explicitly run task-status --refresh.")
    if result["acceptance"]["status"] == "current_declaration" or result["merge_authorization"]["status"] == "current_declaration":
        result["next_actions"].append("Verify the original human messages before any acceptance or merge action.")
    result["summary"] = (f"{task}: {len(result['blockers'])} blockers; PR/CI {result['github']['status']}; "
                         f"Plane {result['plane']['status']}; writeback {result['writeback']['status']} (declaration); "
                         f"handoff {result['handoff']['status']}. No writes performed.")
    return result
