"""Task receipts and evidence gates. No remote writes or automatic state transitions."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from plane_sync import WorkflowError, parse_task, require, sync_provider, state_sync_enabled

SECTIONS = {"brief", "design", "checks", "self_review", "acceptance", "merge_authorization",
            "environment", "delivery"}
SHA = re.compile(r"[0-9a-f]{40}")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def fields(value, allowed, required=()):
    require(isinstance(value, dict) and set(value) <= set(allowed) and set(required) <= set(value),
            "Invalid task record fields; use the task-execution reference. Credentials are not record fields.")


def strings(value, *, nonempty=False):
    require(isinstance(value, list) and all(text(item) for item in value) and
            (not nonempty or bool(value)), "Expected a list of nonempty strings.")


def user_source(source):
    fields(source, {"kind", "reference", "quote"}, {"kind", "reference", "quote"})
    require(source["kind"] == "user_message" and text(source["reference"]) and text(source["quote"]),
            "Acceptance/authorization needs the direct human message reference and quote, not task or PR text.")


def evidence(value, brief_hash):
    require(SHA.fullmatch(value.get("head", "")) is not None and text(value.get("evidence")),
            "Evidence needs an exact commit and an observed result/reference.")
    require(value.get("brief_sha256") == brief_hash, "New evidence must match the current requirement digest.")


def identity(config, task):
    return {"workspace": config["plane"]["workspace"], "project_id": config["plane"]["project_id"],
            "repository": config["github"]["repository"], "base": config["github"]["base_branch"],
            "task": parse_task(task, config)}


def location(root, config, task):
    from plane_workflow import run
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    path = common / "plane-for-codex" / "tasks" / (digest(identity(config, task)) + ".json")
    require(not any(p.is_symlink() for p in (path, path.parent, path.parent.parent)),
            "Task metadata must not resolve through symlinks.")
    return path


def read_record(path, expected_identity):
    if not path.exists():
        return None, "missing"
    raw = path.read_bytes()
    try:
        record = json.loads(raw)
        fields(record, {"version", "identity", "revision", "updated_at", "data", "history"},
               {"version", "identity", "revision", "updated_at", "data", "history"})
        require(record["version"] == 1 and record["identity"] == expected_identity and
                type(record["revision"]) is int and record["revision"] > 0 and
                isinstance(record["history"], list), "Invalid task receipt identity/version.")
        validate(record["data"])
        if "delivery" in record["data"]:
            require(re.fullmatch(re.escape("https://github.com/" + expected_identity["repository"] + "/pull/") + r"[1-9][0-9]*",
                                 record["data"]["delivery"]["pr_url"]) is not None, "Wrong receipt repository.")
    except (ValueError, TypeError, KeyError, WorkflowError):
        raise WorkflowError("Task receipt is invalid. Preserve it and inspect/reconstruct evidence before updating.") from None
    return record, hashlib.sha256(raw).hexdigest()


def validate(data, *, updated=()):
    fields(data, SECTIONS)
    brief = data.get("brief", {})
    criteria = []
    if brief:
        fields(brief, {"goal", "scope", "out_of_scope", "scenarios", "criteria"},
               {"goal", "scope", "out_of_scope", "scenarios", "criteria"})
        require(text(brief["goal"]), "A concrete requirement goal is required.")
        for name in ("scope", "out_of_scope", "scenarios"):
            strings(brief[name], nonempty=name != "out_of_scope")
        require(isinstance(brief["criteria"], list) and bool(brief["criteria"]), "Acceptance criteria are required.")
        for criterion in brief["criteria"]:
            fields(criterion, {"id", "description", "required", "stage"}, {"id", "description", "required", "stage"})
            require(text(criterion["id"]) and re.fullmatch(r"[A-Za-z0-9_-]+", criterion["id"]) is not None and
                    text(criterion["description"]) and type(criterion["required"]) is bool and
                    criterion["stage"] in {"review", "complete"}, "Invalid acceptance criterion.")
            criteria.append(criterion["id"])
        require(len(set(criteria)) == len(criteria), "Duplicate acceptance criterion IDs.")
        require(any(c["required"] for c in brief["criteria"]), "Record at least one required acceptance criterion.")
    brief_hash = digest(brief)
    if "design" in data:
        design = data["design"]
        fields(design, {"required", "status", "evidence", "source", "brief_sha256"},
               {"required", "status", "evidence", "brief_sha256"})
        require(type(design["required"]) is bool and text(design["evidence"]) and
                design["status"] in {"not_required", "proposed", "approved", "provided"}, "Invalid design decision.")
        if design["status"] == "approved":
            user_source(design.get("source"))
        require(design["required"] or design["status"] == "not_required", "Non-required design needs a rationale.")
        require(not design["required"] or design["status"] != "not_required", "Required design needs a confirmed/proposed plan.")
        if "design" in updated:
            require(design["brief_sha256"] == brief_hash, "Design decision belongs to an older requirement.")
    if "checks" in data:
        require(isinstance(data["checks"], list), "Checks must be a list.")
        ids = []
        for check in data["checks"]:
            fields(check, {"id", "criteria", "kind", "status", "head", "evidence", "brief_sha256", "source"},
                   {"id", "criteria", "kind", "status", "head", "evidence", "brief_sha256"})
            require(text(check["id"]) and check["kind"] in
                    {"test", "lint", "build", "visual", "device", "business", "code_review", "sync"} and
                    check["status"] in {"passed", "failed", "not_run", "not_applicable", "accepted_limit", "deferred"},
                    "Invalid verification check.")
            strings(check["criteria"])
            require(SHA.fullmatch(check["head"]) is not None and text(check["evidence"]), "Check needs commit and evidence.")
            if check["status"] == "accepted_limit":
                user_source(check.get("source"))
            if "checks" in updated:
                require(set(check["criteria"]) <= set(criteria), "Check references unknown criteria.")
                evidence(check, brief_hash)
            ids.append(check["id"])
        require(len(set(ids)) == len(ids), "Duplicate check IDs.")
    for name in ("acceptance", "merge_authorization", "self_review"):
        if name not in data or data[name] is None:
            continue
        value = data[name]
        allowed = {"head", "evidence", "brief_sha256"}
        if name != "self_review":
            allowed.add("source")
        if name == "acceptance":
            allowed.add("criteria")
        fields(value, allowed, allowed)
        require(SHA.fullmatch(value["head"]) is not None and text(value["evidence"]), "Invalid evidence receipt.")
        if name != "self_review":
            user_source(value["source"])
        if name == "acceptance":
            strings(value["criteria"], nonempty=True)
            if name in updated:
                require(set(value["criteria"]) <= set(criteria), "Acceptance references unknown criteria.")
        if name in updated:
            evidence(value, brief_hash)
    if "environment" in data:
        require(isinstance(data["environment"], list), "Environment must be a list.")
        for resource in data["environment"]:
            fields(resource, {"name", "owner", "disposition", "evidence", "pid", "port"},
                   {"name", "owner", "disposition", "evidence"})
            require(text(resource["name"]) and text(resource["evidence"]) and
                    resource["owner"] in {"agent", "user", "existing"} and
                    resource["disposition"] in {"keep", "cleanup", "cleaned"}, "Invalid environment ownership.")
            for key in ("pid", "port"):
                if key in resource:
                    require(type(resource[key]) is int and resource[key] > 0 and
                            (key != "port" or resource[key] <= 65535), "Invalid process/port.")
    if "delivery" in data:
        delivery = data["delivery"]
        fields(delivery, {"pr_url", "plane_writeback", "evidence", "head"},
               {"pr_url", "plane_writeback", "evidence", "head"})
        require(text(delivery["pr_url"]) and delivery["plane_writeback"] in {"pending", "confirmed"} and
                text(delivery["evidence"]) and SHA.fullmatch(delivery["head"]) is not None, "Invalid delivery receipt.")


def progress(path, task, *, update=None, expected=None, apply=False):
    from plane_workflow import repo_config, configuration_lock, atomic_write
    root, config = repo_config(path)
    task_identity = identity(config, task)
    destination = location(root, config, task)
    previous, before = read_record(destination, task_identity)
    require(not apply or update is not None, "Supply a record update before applying.")
    if update is None:
        return {"status": "recorded" if previous else "missing", "record_path": str(destination),
                "record_sha256": before, "record": previous,
                "authority": "Recorded declarations, not authenticated authorization or fresh remote proof."}
    fields(update, SECTIONS)
    require(bool(update), "Task update is empty.")
    data = copy.deepcopy(previous["data"] if previous else {})
    data.update(copy.deepcopy(update))
    validate(data, updated=update)
    if "delivery" in data:
        require(re.fullmatch(re.escape("https://github.com/" + config["github"]["repository"] + "/pull/") + r"[1-9][0-9]*",
                             data["delivery"]["pr_url"]) is not None, "Delivery PR belongs to another repository.")
    if expected is not None:
        require(expected == before, "Task record changed; inspect again before applying.")
    now = datetime.now(timezone.utc).isoformat()
    history = copy.deepcopy(previous["history"] if previous else [])
    record = {"version": 1, "identity": task_identity, "revision": (previous["revision"] if previous else 0) + 1,
              "updated_at": now, "data": data, "history": history}
    # Preserve previous facts for inspection; only data drives current decisions.
    if previous and data != previous["data"]:
        history.append({"revision": previous["revision"], "updated_at": previous["updated_at"], "data": previous["data"]})
    result = {"status": "planned", "record_path": str(destination), "expected_record_sha256": before,
              "brief_sha256": digest(data.get("brief", {})), "record": record}
    if apply:
        require(expected == before, "Apply with --expected-record-sha256 from the inspected plan.")
        with configuration_lock(root):
            require(repo_config(root)[1] == config, "Mapping changed while recording task progress.")
            require(read_record(destination, task_identity)[1] == before, "Task record changed concurrently; inspect again.")
            if previous and data == previous["data"]:
                result.update(status="unchanged", record=previous, record_sha256=before)
                return result
            location(root, config, task)
            destination.parent.mkdir(exist_ok=True)
            atomic_write(destination, (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
        result.update(status="recorded", record_sha256=read_record(destination, task_identity)[1])
    return result


def gates(data, head, stage, *, manual=True):
    require(stage in {"implement", "review", "merge", "complete"}, "Invalid task check stage.")
    blockers, limitations = [], []
    brief = data.get("brief", {})
    brief_hash = digest(brief)
    if not brief:
        blockers.append("requirements_missing")
    design = data.get("design", {})
    if not design or design.get("brief_sha256") != brief_hash:
        blockers.append("design_decision_missing_or_stale")
    elif design["required"] and design["status"] not in {"approved", "provided"}:
        blockers.append("design_confirmation_required")
    if stage != "implement":
        review = data.get("self_review") or {}
        if review.get("head") != head or review.get("brief_sha256") != brief_hash:
            blockers.append("self_review_missing_or_stale")
        checks = data.get("checks", [])
        for criterion in brief.get("criteria", []):
            relevant = [c for c in checks if criterion["id"] in c["criteria"] and c["kind"] != "sync"]
            current = [c for c in relevant if c["head"] == head and c["brief_sha256"] == brief_hash]
            satisfied = bool(current) and all(c["status"] in {"passed", "not_applicable", "accepted_limit"} for c in current)
            if not satisfied:
                item = "criterion_unverified:" + criterion["id"]
                if criterion["required"] and (criterion["stage"] == "review" or stage == "complete"):
                    blockers.append(item)
                else:
                    limitations.append(item)
        acceptance = data.get("acceptance") or {}
        required = {c["id"] for c in brief.get("criteria", []) if c["required"]}
        accepted = (acceptance.get("head") == head and acceptance.get("brief_sha256") == brief_hash and
                    required <= set(acceptance.get("criteria", [])))
        if stage == "complete" and manual and not accepted:
            blockers.append("human_acceptance_missing_or_stale")
        if stage == "merge":
            authorization = data.get("merge_authorization") or {}
            if authorization.get("head") != head or authorization.get("brief_sha256") != brief_hash:
                blockers.append("merge_authorization_missing_or_stale")
        if stage == "complete":
            delivery = data.get("delivery", {})
            if delivery.get("plane_writeback") != "confirmed" or delivery.get("head") != head:
                blockers.append("delivery_writeback_pending_or_stale")
            if any(r["owner"] == "agent" and r["disposition"] == "cleanup" for r in data.get("environment", [])):
                blockers.append("agent_environment_cleanup_pending")
    return {"stage": stage, "ready": not blockers, "blockers": blockers, "limitations": limitations}


def check_task(path, task, stage, *, workitem=None):
    from plane_workflow import repo_config, run
    root, config = repo_config(path)
    receipt = progress(root, task)
    data = receipt["record"]["data"] if receipt["record"] else {}
    head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
    local_head = head
    pr = None
    remote_blockers = []
    manual = True
    if stage == "complete":
        try:
            fields(workitem, {"task", "project_id", "labels", "state_group", "observed_at"},
                   {"task", "project_id", "labels", "state_group", "observed_at"})
            require(workitem["task"] == parse_task(task, config) and workitem["project_id"] == config["plane"]["project_id"],
                    "Live work item does not match the task.")
            strings(workitem["labels"])
            require(text(workitem["state_group"]), "Cannot resolve the live task state group.")
            observed = datetime.fromisoformat(workitem["observed_at"].replace("Z", "+00:00"))
            require(observed.tzinfo is not None and 0 <= (datetime.now(timezone.utc) - observed).total_seconds() <= 300,
                    "Read the current Plane task before completion; the snapshot is stale.")
            manual = config["completion"]["policy"] == "manual" or config["completion"].get("manual_label", "manual-acceptance") in workitem["labels"]
            if workitem["state_group"] in {"cancelled", "canceled"}:
                remote_blockers.append("cancelled_task_preserved")
        except (WorkflowError, ValueError, TypeError, KeyError, AttributeError):
            remote_blockers.append("live_plane_task_unverified")
    if stage in {"merge", "complete"}:
        url = data.get("delivery", {}).get("pr_url")
        if not url:
            remote_blockers.append("primary_pr_missing")
        else:
            try:
                pr = json.loads(run(["gh", "pr", "view", url, "--json",
                                     "url,state,isDraft,headRefOid,baseRefName,mergeCommit,title,body,isCrossRepository,mergeable,mergeStateStatus"], root).stdout)
                from plane_sync import pr_task
                require(pr["url"] == url and pr["baseRefName"] == config["github"]["base_branch"] and
                        not pr["isCrossRepository"] and pr_task(pr, config) == parse_task(task, config),
                        "Live PR binding does not match the task.")
                head = pr["headRefOid"]
                require(SHA.fullmatch(head) is not None, "Invalid live PR commit.")
                response = run(["gh", "pr", "checks", url, "--required", "--json", "name,bucket"], root, check=False)
                require(response.returncode in {0, 1, 8}, "Cannot read required PR checks.")
                # gh emits a non-JSON diagnostic when its required-context list is empty.
                # Accept only its exact known diagnostic; auth/network failures stay unknown.
                no_checks = response.returncode == 1 and not response.stdout.strip() and re.fullmatch(
                    r"no (?:required )?checks reported on the '[^\n]+' branch\n?", response.stderr) is not None
                checks = [] if no_checks else json.loads(response.stdout)
                require(isinstance(checks, list) and
                        all(isinstance(c, dict) and c.get("bucket") in {"pass", "fail", "pending", "skipping", "cancel"}
                            for c in checks), "Invalid required PR checks.")
                if any(c["bucket"] != "pass" for c in checks):
                    remote_blockers.append("required_github_checks_not_passed")
                if stage == "merge":
                    if head != local_head:
                        remote_blockers.append("local_pr_head_mismatch")
                    if pr["state"] != "OPEN" or pr["isDraft"]:
                        remote_blockers.append("pr_not_open_ready_for_merge")
                    if pr.get("mergeable") != "MERGEABLE" or pr.get("mergeStateStatus") not in {"CLEAN", "UNSTABLE"}:
                        remote_blockers.append("pr_mergeability_unverified_or_blocked")
                elif pr["state"] != "MERGED" or not (pr.get("mergeCommit") or {}).get("oid"):
                    remote_blockers.append("pr_not_merged")
            except (WorkflowError, ValueError, KeyError, TypeError):
                remote_blockers.append("live_pr_or_checks_unverified")
    result = gates(data, head, stage, manual=manual)
    if stage != "complete":
        from checkout_workflow import inspect
        result["checkout_check"] = inspect(root, config, task)
        result["blockers"].extend(result["checkout_check"]["blockers"])
    if stage in {"review", "merge"} and run(["git", "status", "--porcelain"], root).stdout.strip():
        result["blockers"].append("uncommitted_changes_not_covered")
    result["blockers"].extend(remote_blockers)
    result.update(ready=not result["blockers"], task=parse_task(task, config), head=head, pr=pr,
                  provider=sync_provider(config), state_sync=state_sync_enabled(config),
                  record_sha256=receipt["record_sha256"],
                  authority="Receipt sources are agent declarations. Verify original human messages before authorized actions; no writes performed.")
    return result


def report(path, task, summary, *, stage="review", workitem=None):
    from plane_workflow import repo_config
    root, config = repo_config(path)
    receipt = progress(root, task)
    require(receipt["record"] is not None, "Record task progress before rendering a structured report.")
    data = receipt["record"]["data"]
    result = check_task(root, task, stage, workitem=workitem)
    require(result["record_sha256"] == receipt["record_sha256"], "Task record changed while rendering; inspect and render again.")
    brief_hash = digest(data.get("brief", {}))
    head = result["head"]
    lines = [f"Observed commit: `{head}`. Task receipt revision: {receipt['record']['revision']}."]
    lines.append(f"{stage} gate: {'ready' if result['ready'] else 'blocked'}; verification declarations require inspection.")
    for c in data.get("checks", []):
        status = c["status"] if c["head"] == head and c["brief_sha256"] == brief_hash else "stale"
        lines.append(f"- {c['id']} ({c['kind']}, {status}): {c['evidence']}")
    acceptance = data.get("acceptance") or {}
    accepted = acceptance.get("head") == head and acceptance.get("brief_sha256") == brief_hash
    remaining = ["Implementation acceptance: " + ("recorded for listed criteria only; verify original user context." if accepted else "not recorded for this commit.")]
    if accepted:
        remaining.append("Accepted criteria: " + ", ".join(acceptance["criteria"]))
    remaining += ["- " + item for item in result["blockers"] + result["limitations"]]
    for criterion in data.get("brief", {}).get("criteria", []):
        remaining.append(f"- {criterion['id']} ({'required' if criterion['required'] else 'optional'}, {criterion['stage']}): {criterion['description']}")
    for resource in data.get("environment", []):
        remaining.append(f"- Environment {resource['name']}: {resource['owner']}, {resource['disposition']}; {resource['evidence']}")
    if result["pr"]:
        remaining.append(f"Observed GitHub PR: {result['pr']['url']} ({result['pr']['state']}).")
    else:
        remaining.append("PR lifecycle is verified separately from GitHub; this report does not infer merge or completion.")
    from plane_workflow import render_report
    body = render_report(root, task, summary, "\n".join(lines), "\n".join(remaining))
    stamp = {"version": 1, "head": head, "brief_sha256": brief_hash, "record_sha256": receipt["record_sha256"]}
    return body + "\n<!-- plane-for-codex-evidence " + json.dumps(stamp, separators=(",", ":")) + " -->\n"


def verify_report(body, receipt_hash, head, brief_hash):
    stamps = re.findall(r"<!-- plane-for-codex-evidence (.*?) -->", body)
    require(len(stamps) == 1, "Use render-report --from-progress to bind the report to current evidence.")
    try:
        stamp = json.loads(stamps[0])
    except ValueError:
        raise WorkflowError("Invalid report evidence stamp.") from None
    require(stamp == {"version": 1, "head": head, "brief_sha256": brief_hash, "record_sha256": receipt_hash},
            "Report evidence is stale; regenerate the report from current task progress.")
