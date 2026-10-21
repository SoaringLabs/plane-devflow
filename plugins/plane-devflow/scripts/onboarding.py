"""Capability-aware setup recovery. Local receipts are hints, never remote proof."""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from github_setup import assess, check, config_digest
from plane_sync import WorkflowError, require, sync_provider

SURFACES = {"browser-control", "app-control", "url-opener"}
EVENTS = {"pat-ready", "pat-unavailable", "secret-saved"}


def capabilities(surfaces=()):
    require(set(surfaces) <= SURFACES, "Report only supported host surfaces.")
    available = set(surfaces)
    route = next((name for name in ("browser-control", "app-control", "url-opener") if name in available), "manual-links")
    return {"git": bool(shutil.which("git")), "github_cli": bool(shutil.which("gh")),
            "node": bool(shutil.which("node")), "npm": bool(shutil.which("npm")),
            "codex_cli": bool(shutil.which("codex")),
            "host_surfaces": sorted(available), "guidance_route": route,
            "host_source": "caller_reports_current_tool_availability",
            "plane_desktop_required": False, "manual_guidance_available": True,
            "authentication": "unknown_until_service_probe",
            "credential_transfer": "human_only",
            "plane_app_creation": {"platform_supported": sys.platform == "darwin", "session": "not_inspected",
                                   "authorization_required": True}}


def checkpoint_path(root, config):
    from plane_workflow import run
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    destination = common / "plane-devflow" / "setup" / (config_digest(config) + ".json")
    require(not any(p.is_symlink() for p in (destination, destination.parent, destination.parent.parent)),
            "Setup progress must not resolve through symlinks.")
    return destination


def receipt(path, digest):
    if not path.exists():
        return {}, "new"
    try:
        data = json.loads(path.read_text())
        require(set(data) == {"version", "config_sha256", "reported_step", "observed_at", "remote_checks"} and
                data["version"] == 1 and data["config_sha256"] == digest and
                data["reported_step"] in EVENTS | {None}, "Invalid checkpoint.")
        require(isinstance(data["observed_at"], str) and datetime.fromisoformat(data["observed_at"]).tzinfo is not None,
                "Invalid checkpoint time.")
        require(isinstance(data["remote_checks"], dict) and
                set(data["remote_checks"]) <= {"actions_enabled", "workflow_active", "remote_files_match", "sync_bundle_verified", "remote_config_matches", "secret_present", "connection_verified", "native_mapping_verified"} and
                all(value is None or type(value) is bool for value in data["remote_checks"].values()), "Invalid checkpoint checks.")
        return data, "resumed"
    except (WorkflowError, OSError, ValueError, TypeError, KeyError):
        return {}, "invalid"


def next_step(report, reported):
    if report["provider"] == "native":
        return "native_verified" if report["github_sync"] == "ready" else "verify_native_mapping"
    checks = report["checks"]
    # Known operational blockers come before another credential request.
    if checks.get("actions_enabled") is False:
        return "enable_actions"
    problems = report.get("issues", [])
    if problems:
        if any(p["code"] == "authentication_required" for p in problems):
            return "login_github"
        if any(p["code"] == "permission_denied" for p in problems):
            return "resolve_permissions"
        if any(p["retryable"] for p in problems):
            return "retry_checks_later"
    if checks.get("secret_present") is None:
        return "verify_secret_metadata"
    if checks["secret_present"] is False:
        if reported == "secret-saved":
            return "check_secret_repository_name_and_scope"
        if reported == "pat-ready":
            return "confirm_pat_available_then_github"
        return "local_credential"
    if report.get("sync_bundle", {}).get("upgrade_required") is True:
        return "review_sync_bundle_upgrade"
    if report.get("sync_bundle", {}).get("status") == "unrecognized":
        return "review_sync_bundle_files"
    if any(checks.get(k) is not True for k in ("workflow_active", "sync_bundle_verified", "remote_config_matches")):
        return "review_default_branch_setup"
    if report.get("connection", {}).get("status") == "refresh_due":
        return "refresh_connection_evidence"
    if checks.get("connection_verified") is not True:
        return "inspect_connection_failure" if report.get("evidence", {}).get("connection_conclusion") == "failure" else "run_connection_check"
    return "connection_verified"


def progress(path, *, surfaces=(), offline=False, event=None, apply=False, cache=False, refresh=False):
    from plane_workflow import repo_config, configuration_lock, atomic_write, credential_guide
    require(event is None or event in EVENTS, "Use a non-secret progress event.")
    root, config = repo_config(path)
    caps = capabilities(surfaces)
    digest = config_digest(config)
    destination = checkpoint_path(root, config)
    previous, recovery = receipt(destination, digest)
    require(not (apply and recovery == "invalid"),
            "Checkpoint is invalid. Keep it for local inspection; read-only recovery can reconstruct remote state.")
    provider = sync_provider(config)
    require(event is None or provider == "actions", "Native mode skips all runner credential events.")
    if provider == "native":
        report = check(root)  # Local exact-config observation, no GitHub requests.
    elif offline or not caps["github_cli"]:
        report = assess(config)
        if not offline:
            from setup_errors import issue
            report["issues"] = [issue("cli_unavailable", "github")]
    else:
        from sync_health import status
        report = status(root, persist=cache, refresh=refresh or event == "secret-saved", probe=check)
    reported = event if event is not None else previous.get("reported_step")
    step = next_step(report, reported)
    result = {"version": 1, "provider": provider, "repository": config["github"]["repository"],
              "config_sha256": digest, "capabilities": caps, "recovery": recovery,
              "checkpoint_path": str(destination), "checkpoint_written": False,
              "reported_step": reported, "reported_step_source": "user_confirmation" if reported else None,
              "next_step": step, "readiness": report, "event_writeback_verified": None,
              "sync_bundle": report.get("sync_bundle"), "maintenance_notice": report.get("sync_bundle_notice"),
              "cached_checks_reused_as_proof": False, "merge_authorization": "use_current_user_authorization"}
    from first_project import handoff
    result["handoff"] = handoff(root, step)
    result["handoff"].update(repository=config["github"]["repository"], project_id=config["plane"]["project_id"],
                             config_sha256=digest, checkpoint_path=str(destination))
    result["handoff"]["resume_prompt"] += (f" Expected mapping: {digest}, project {config['plane']['project_id']}, "
                                             f"repository {config['github']['repository']}. Inspect any mismatch before writes.")
    result["next_user_action"] = ("Describe the first version to draft tasks; creation requires approval of the exact list."
                                  if step in {"connection_verified", "native_verified"}
                                  else "Complete only the reported next step, then refresh setup-progress.")
    if provider == "actions":
        if step in {"local_credential", "confirm_pat_available_then_github", "check_secret_repository_name_and_scope", "verify_secret_metadata"}:
            result["credential_guide"] = credential_guide(root, step="local" if step == "local_credential" else "github")
        if step == "verify_secret_metadata":
            result["manual_storage_option"] = "Existing PAT may be saved through the linked repository Secret page; unknown metadata does not require a new PAT. Automatic verification remains pending."
    if apply:
        with configuration_lock(root):
            require(repo_config(root)[1] == config, "Configuration changed; inspect and resume with the new mapping.")
            current, current_status = receipt(destination, digest)
            require(current == previous and current_status == recovery, "Progress changed concurrently; inspect again before saving.")
            destination.parent.mkdir(exist_ok=True)
            checkpoint_path(root, config)
            # Keep v1 receipts readable by older plugin sessions sharing this repo.
            # Bundle compatibility is always probed again, never restored as proof.
            historical = {key: value for key, value in report["checks"].items() if key != "sync_bundle_verified"}
            payload = {"version": 1, "config_sha256": digest, "reported_step": reported,
                       "observed_at": datetime.now(timezone.utc).isoformat(), "remote_checks": historical}
            atomic_write(destination, (json.dumps(payload, indent=2) + "\n").encode())
            result["checkpoint_written"] = True
    return result
