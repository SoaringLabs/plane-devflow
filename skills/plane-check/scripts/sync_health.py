"""Daily, non-secret Git-metadata cache. Never dispatches workflows or calls Plane."""
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from github_setup import (check, config_digest, describe_health, EVIDENCE_TTL_SECONDS,
                          _github_timestamp)
from plane_sync import require


def cache_path(root, config):
    from plane_workflow import run
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    path = common / "plane-devflow" / "sync-health" / (config_digest(config) + ".json")
    require(not any(p.is_symlink() for p in (common / "plane-devflow", path.parent, path)),
            "Sync health cache must not resolve through symlinks.")
    return path


def read_cache(path, config, now):
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
        require(set(value) == {"version", "config_sha256", "probed_at", "report"} and
                type(value["version"]) is int and value["version"] == 1 and
                value["config_sha256"] == config_digest(config) and
                isinstance(value["report"], dict) and isinstance(value["report"]["checks"], dict),
                "Invalid sync health cache; preserve it and inspect before refreshing.")
        require(_github_timestamp(value["probed_at"]) <= now, "Sync health cache has a future timestamp.")
        return value
    except (ValueError, TypeError, KeyError):
        require(False, "Invalid sync health cache; preserve it and inspect before refreshing.")


def status(path, *, refresh=False, persist=False, offline=False, now=None, probe=None):
    """persist opts into cache-only writes; ordinary checks leave all files unchanged."""
    from plane_workflow import repo_config, configuration_lock, atomic_write
    root, config = repo_config(path)
    now = now or datetime.now(timezone.utc)
    destination = cache_path(root, config)
    probe = probe or check

    def inspect():
        previous = read_cache(destination, config, now)
        recent = previous and (now - _github_timestamp(previous["probed_at"])).total_seconds() < EVIDENCE_TTL_SECONDS
        if previous and (offline or (recent and not refresh)):
            report = describe_health(previous["report"], config, now=now)
            if offline:
                report.update(initialization="partial", github_sync="unverified", message="离线检查：显示历史记录，当前连接未验证。")
                report["checks"] = {k: None for k in report["checks"]}
                report["connection"]["status"] = "unknown_offline"
            return report, previous["probed_at"], "cached", False
        if offline:
            from github_setup import assess
            report = describe_health(assess(config), config, now=now)
            return report, None, "offline", False
        report = probe(root)
        # The live probe owns its observation time; only cached facts need reassessment.
        if persist:
            require(repo_config(root)[1] == config, "Mapping changed during synchronization check.")
            cache_path(root, config)
            destination.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(destination, (json.dumps({"version": 1, "config_sha256": config_digest(config),
                "probed_at": now.isoformat(), "report": report}, ensure_ascii=False, indent=2) + "\n").encode())
        return report, now.isoformat(), "remote_probe", persist

    if persist and not offline:
        with configuration_lock(root):
            require(repo_config(root)[1] == config, "Mapping changed before synchronization check.")
            report, probed_at, source, written = inspect()
    else:
        report, probed_at, source, written = inspect()
    report = copy.deepcopy(report)
    next_probe = (_github_timestamp(probed_at) + timedelta(seconds=EVIDENCE_TTL_SECONDS)).isoformat() if probed_at else None
    report["observation"] = {"source": source, "probed_at": probed_at, "next_routine_probe_at": next_probe,
                             "cache_written": written, "interval_seconds": EVIDENCE_TTL_SECONDS,
                             "freshness": "unknown" if offline else "historical" if source == "cached" else "observed",
                             "connection_probe_dispatched": False}
    return report
