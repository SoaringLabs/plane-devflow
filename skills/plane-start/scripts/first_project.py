"""Read-only local bootstrap inspection; no installs, credentials or service calls."""
import re
import subprocess
import sys
from pathlib import Path

from plane_sync import CONFIG_NAME, WorkflowError, require


def handoff(path, step):
    """Portable context, deliberately excluding consent and cached service success."""
    target = str(Path(path).expanduser().resolve())
    require(not any(c in target for c in "\n\r\x00"), "Use a single-line target directory.")
    return {"target_directory": target, "next_step": step,
            "resume_prompt": f"Continue Plane DevFlow onboarding for {target}. "
                             f"The previous next step was {step}. Recheck current prerequisites, "
                             "connections and existing resources before continuing. Recover the original "
                             "user decisions; this handoff supplies context, not authorization.",
            "authorization": "recover_original_user_messages", "cached_checks_reused_as_proof": False}


def node_version(executable):
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=5)
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)\s*", result.stdout) if result.returncode == 0 else None
        return tuple(map(int, match.groups())) if match else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def status(path, *, surfaces=(), channel="skills"):
    from onboarding import capabilities
    from plane_workflow import run, github_repo, repo_config
    import shutil
    require(channel in {"skills", "plugin", "installed"}, "Choose the intended installation channel.")
    target = Path(path).expanduser().resolve()
    caps = capabilities(surfaces)
    node = node_version(shutil.which("node"))
    checks = {"git": caps["git"], "python_supported": sys.version_info >= (3, 10),
              "node_supported": node >= ((22, 20, 0) if channel == "skills" else (20, 0, 0)) if node else None,
              "npm": bool(shutil.which("npm")), "github_cli": caps["github_cli"],
              "target_exists": target.is_dir(), "git_repository": False,
              "initial_commit": False, "github_origin": False, "mapping": "absent"}
    if checks["git"] and target.is_dir():
        probe = run(["git", "rev-parse", "--show-toplevel"], target, check=False)
        if probe.returncode == 0:
            # Do not silently adopt a parent repository for a requested new directory.
            checks["git_repository"] = Path(probe.stdout.strip()).resolve() == target
        if checks["git_repository"]:
            checks["initial_commit"] = run(["git", "rev-parse", "--verify", "HEAD"], target, check=False).returncode == 0
            remote = run(["git", "remote", "get-url", "origin"], target, check=False)
            if remote.returncode == 0:
                try:
                    github_repo(remote.stdout.strip())
                    checks["github_origin"] = True
                except WorkflowError:
                    pass
            if (target / CONFIG_NAME).exists():
                try:
                    repo_config(target)
                    checks["mapping"] = "valid"
                except WorkflowError:
                    checks["mapping"] = "invalid_or_mismatched"
    required = ["git", "python_supported", "github_cli"]
    if channel != "installed":
        required += ["node_supported", "npm"]
    if channel == "plugin":
        checks["codex_cli"] = caps["codex_cli"]
        required.append("codex_cli")
    if not all(checks[k] is True for k in required):
        step = "prepare_missing_tools"
    elif not checks["git_repository"]:
        step = "prepare_repository"
    elif not checks["initial_commit"]:
        step = "prepare_initial_commit"
    elif not checks["github_origin"]:
        step = "connect_github_repository"
    elif checks["mapping"] == "invalid_or_mismatched":
        step = "inspect_existing_mapping"
    elif checks["mapping"] == "valid":
        step = "resume_setup_progress"
    else:
        step = "verify_accounts_and_select_project"
    return {"mode": "read_only_bootstrap", "installation_channel": channel, "required_checks": required,
            "checks": checks, "capabilities": caps,
            "node_version": list(node) if node else None, "next_step": step,
            "host_checks_pending": ["skills_loaded", "github_authentication", "plane_workspace_access"],
            "initialization": "unverified", "handoff": handoff(target, step),
            "files_written": False, "services_called": False}
