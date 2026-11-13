"""Identify serial task executions. These local records are not ownership locks."""
from datetime import datetime, timezone
import json
import re
from uuid import uuid4

from plane_sync import require
from task_progress import fields, identity

AGENT_PREFIXES = {"codex": "codex", "claude-code": "claude", "cursor": "cursor", "opencode": "opencode"}


def agent_name(agent):
    value = agent or "unknown"
    require(isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value) is not None,
            "Agent must be a lowercase host identifier, e.g. claude-code.")
    return value


def read_execution(root, config, task):
    from checkout_workflow import metadata_path, read_metadata
    record, stamp = read_metadata(metadata_path(root, config, task, "executions"), identity(config, task))
    if record:
        fields(record, {"version", "identity", "current", "history"}, {"version", "identity", "current", "history"})
        require(isinstance(record["history"], list), "Invalid execution history; preserve the record.")
        for entry in [record["current"], *record["history"]]:
            fields(entry, {"id", "agent", "session_id", "started_at"}, {"id", "agent", "session_id", "started_at"})
            require(isinstance(entry["id"], str) and re.fullmatch(r"run-[0-9a-f]{32}", entry["id"]) is not None,
                    "Invalid execution ID; preserve the record.")
            agent_name(entry["agent"])
            require(entry["session_id"] is None or isinstance(entry["session_id"], str) and
                    0 < len(entry["session_id"]) <= 256, "Invalid execution session reference.")
            require(isinstance(entry["started_at"], str), "Invalid execution timestamp.")
    return record, stamp


def execution(root, config, task, *, agent=None, execution_id=None, session_id=None, apply=False):
    from checkout_workflow import metadata_path
    from plane_workflow import atomic_write, configuration_lock, repo_config
    host = agent_name(agent)
    require(session_id is None or isinstance(session_id, str) and 0 < len(session_id) <= 256,
            "Session reference must be a nonempty string of at most 256 characters.")
    previous, stamp = read_execution(root, config, task)
    current = previous["current"] if previous else None
    if execution_id is not None:
        require(current is not None and execution_id == current["id"],
                "Execution ID is not the current task execution. Inspect prepare and start a new execution if needed.")
        require(agent is None or host == current["agent"], "Execution ID belongs to a different agent.")
        require(session_id is None or session_id == current["session_id"],
                "Execution ID belongs to a different session.")
    reuse = execution_id is not None or bool(current and session_id is not None and
                                            current["agent"] == host and current["session_id"] == session_id)
    result = {"action": "reuse" if reuse else "new", "current": current,
              "agent": current["agent"] if reuse else host,
              "authority": "Execution identifiers only; no lock, liveness check or takeover decision."}
    if not apply:
        return result
    with configuration_lock(root):
        require(repo_config(root)[1] == config and read_execution(root, config, task)[1] == stamp,
                "Task execution or mapping changed. Inspect again before recording.")
        if not reuse:
            current = {"id": "run-" + uuid4().hex, "agent": host, "session_id": session_id,
                       "started_at": datetime.now(timezone.utc).isoformat()}
            history = [*previous["history"], previous["current"]] if previous else []
            record = {"version": 1, "identity": identity(config, task), "current": current, "history": history}
            destination = metadata_path(root, config, task, "executions")
            destination.parent.mkdir(exist_ok=True)
            atomic_write(destination, (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
    result["current"] = current
    return result
