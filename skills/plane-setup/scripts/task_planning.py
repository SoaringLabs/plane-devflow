"""Project-bound first-task drafts and reconciliation. Remote writes belong to MCP."""
import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from github_setup import config_digest
from plane_sync import require


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def validate(plan):
    require(isinstance(plan, dict) and set(plan) == {"version", "goal", "tasks"} and
            type(plan["version"]) is int and plan["version"] == 1 and text(plan["goal"]), "Invalid task plan header.")
    require(isinstance(plan["tasks"], list) and bool(plan["tasks"]), "A task plan needs at least one task.")
    seen, names = set(), set()
    for task in plan["tasks"]:
        require(isinstance(task, dict) and set(task) == {"key", "name", "description", "criteria", "depends_on"},
                "Each task needs key, name, description, criteria and depends_on.")
        key = task["key"]
        require(isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,47}", key) and key not in seen,
                "Task keys must be unique lowercase identifiers.")
        require(text(task["name"]) and len(task["name"]) <= 255 and task["name"].strip().casefold() not in names,
                "Task titles must be distinct and at most 255 characters.")
        require(text(task["description"]), "Describe each task's scope and exclusions.")
        require(isinstance(task["criteria"], list) and bool(task["criteria"]) and all(text(c) for c in task["criteria"]),
                "Each task needs observable acceptance criteria.")
        deps = task["depends_on"]
        require(isinstance(deps, list) and all(isinstance(d, str) and d in seen for d in deps) and len(deps) == len(set(deps)),
                "List dependencies before dependent tasks; self/unknown/cyclic dependencies are invalid.")
        seen.add(key)
        names.add(task["name"].strip().casefold())
    return plan


def location(root, config, plan_id):
    from plane_workflow import run
    require(isinstance(plan_id, str) and re.fullmatch(r"[a-f0-9]{64}", plan_id), "Invalid plan ID.")
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    path = common / "plane-devflow" / "task-plans" / config_digest(config) / (plan_id + ".json")
    current = path
    while current != current.parent:
        require(not current.is_symlink(), "Task plans must not resolve through symlinks.")
        if current == common:
            break
        current = current.parent
    require(not path.exists() or path.is_file(), "Saved plans must be regular files.")
    return path


def snapshot(data, project):
    require(isinstance(data, dict) and set(data) == {"project_id", "observed_at", "complete", "workitems"} and
            data["project_id"] == project and data["complete"] is True and isinstance(data["workitems"], list),
            "Supply a complete live snapshot of this project's work items, including all pages.")
    try:
        raw = data["observed_at"]
        observed = datetime.fromisoformat(raw.replace("Z", "+00:00")) if isinstance(raw, str) else None
        fresh = observed is not None and observed.tzinfo is not None and 0 <= (datetime.now(timezone.utc) - observed).total_seconds() <= 300
    except (TypeError, ValueError):
        fresh = False
    require(fresh, "Refresh the project snapshot through MCP before reconciliation.")
    ids = set()
    for item in data["workitems"]:
        require(isinstance(item, dict) and item.get("project_id") == project and text(item.get("name")) and
                all(k in item and (item[k] is None or isinstance(item[k], str)) for k in ("external_id", "external_source")),
                "Snapshot items need project_id, name, external_id and external_source (request these fields explicitly).")
        try:
            valid = str(uuid.UUID(item.get("id"))) == item["id"] and item["id"] not in ids
        except (ValueError, TypeError, AttributeError):
            valid = False
        require(valid, "Snapshot item IDs must be unique UUIDs.")
        ids.add(item["id"])
    return data["workitems"]


def progress(path, *, plan=None, plan_id=None, existing=None, expected=None, apply=False):
    from plane_workflow import repo_config, configuration_lock, atomic_write
    root, config = repo_config(path)
    require((plan is None) != (plan_id is None), "Supply a new draft or a saved plan ID.")
    if plan is None:
        destination = location(root, config, plan_id)
        saved = json.loads(destination.read_text())
        require(isinstance(saved, dict) and set(saved) == {"version", "config_sha256", "plan_id", "plan"} and
                type(saved["version"]) is int and saved["version"] == 1 and
                saved["config_sha256"] == config_digest(config) and saved["plan_id"] == plan_id,
                "Saved plan does not belong to the current repository mapping.")
        plan = saved["plan"]
    validate(plan)
    computed = digest({"config_sha256": config_digest(config), "plan": plan})
    require(plan_id is None or plan_id == computed, "Saved plan content changed; inspect it before continuing.")
    plan_id = computed
    destination = location(root, config, plan_id)
    payload = {"version": 1, "config_sha256": config_digest(config), "plan_id": plan_id, "plan": plan}
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    require(not destination.exists() or destination.read_bytes() == encoded, "Saved plan changed; preserve it and inspect before retrying.")
    operations, blockers = [], []
    items = snapshot(existing, config["plane"]["project_id"]) if existing is not None else None
    for task in plan["tasks"]:
        external_id = f"task-plan:{plan_id}:{task['key']}"
        description = "<p>" + html.escape(task["description"]).replace("\n", "<br>") + "</p><ul>" + "".join(
            "<li>" + html.escape(c) + "</li>" for c in task["criteria"]) + "</ul>"
        operation = {"key": task["key"], "name": task["name"], "description_html": description,
                     "external_id": external_id, "external_source": "plane-devflow",
                     "depends_on": task["depends_on"], "action": "inspect_live_project", "existing_id": None}
        if items is not None:
            matches = [i for i in items if i["external_id"] == external_id and i["external_source"] == "plane-devflow"]
            lookalikes = [i for i in items if i["name"].strip().casefold() == task["name"].strip().casefold()]
            if len(matches) > 1 or (not matches and lookalikes):
                operation["action"] = "reconcile_conflict"
                blockers.append({"key": task["key"], "reason": "duplicate_marker_or_unbound_title"})
            elif matches:
                operation.update(action="reuse", existing_id=matches[0]["id"])
            else:
                operation["action"] = "create_after_user_approval"
        operations.append(operation)
    if apply:
        require(expected == plan_id, "Inspect the draft digest before saving it.")
        with configuration_lock(root):
            require(repo_config(root)[1] == config, "Mapping changed; replan for the selected project.")
            location(root, config, plan_id)
            destination.parent.mkdir(parents=True, exist_ok=True)
            location(root, config, plan_id)
            require(not destination.exists() or destination.read_bytes() == encoded, "Saved plan changed concurrently.")
            if not destination.exists():
                atomic_write(destination, encoded)
    return {"plan_id": plan_id, "plan": plan, "project_id": config["plane"]["project_id"],
            "repository": config["github"]["repository"], "plan_path": str(destination),
            "saved": destination.exists(), "operations": operations, "blockers": blockers,
            "reconciliation": "pending_live_snapshot" if items is None else "blocked" if blockers else "checked",
            "remote_writes_performed": False, "authorization": "verify_original_user_approval_for_this_exact_plan",
            "resume_prompt": f"Resume first-task planning with plan {plan_id} in {root}. "
                             "Read the saved draft, verify original user approval, and refresh all project work items "
                             "through MCP before creating only missing tasks. Saved drafts do not grant consent."}
