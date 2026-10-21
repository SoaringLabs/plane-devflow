"""Install repository-local sync and assess setup without reading secret values."""
import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from plane_sync import CONFIG_NAME, WorkflowError, require, state_sync_enabled, sync_provider, api_version, validate_config

from sync_bundle import (WORKFLOW, BUNDLE, CHECKOUT_SHA, bundled_files, bundled_workflow, inspect_bundle)

IMPACT = ("GitHub 上创建、更新或合并 PR 后，这些事件无法自动同步到 Plane，"
          "也不会触发对应的任务状态转换。Codex 内的 Plane 操作仍可使用；"
          "GitHub 上发生的变化需要回到 Codex 中检查并同步。")


def install(root, *, apply=False, upgrade=False, expected_files_sha256=None):
    from plane_workflow import configuration_lock, repo_config, snapshot, atomic_write
    root, config = repo_config(root)
    if sync_provider(config) == "native":
        return {"status": "skipped", "provider": "native", "files": [],
                "next_step": "核对官方集成的仓库、项目映射和状态规则，再记录原生验证凭据；不需要 Actions Secret。"}
    files = bundled_files()
    before = {}
    for name in files:
        path = root / name
        require(not any(parent.is_symlink() for parent in [path, *path.parents]
                        if parent == root or root in parent.parents), "Sync files must not resolve through symlinks.")
        before[name] = snapshot(path)[1]
    before[CONFIG_NAME] = snapshot(root / CONFIG_NAME)[1]
    digest = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()
    changes = {name: {"before": before[name], "after": hashlib.sha256(data).hexdigest()}
               for name, data in files.items() if before[name] != hashlib.sha256(data).hexdigest()}
    conflicts = [name for name in changes if before[name] != "missing"]
    require(not conflicts or upgrade,
            "Existing sync files differ. Review setup-github --upgrade before replacing them.")
    if expected_files_sha256 is not None:
        require(expected_files_sha256 == digest, "Sync files or mapping changed since the plan. Inspect and retry.")
    require(not (apply and conflicts) or expected_files_sha256 == digest,
            "Apply an upgrade with --expected-files-sha256 from the reviewed plan.")
    result = {"status": "prepared" if apply else "planned", "files": list(files), "changes": changes,
              "expected_files_sha256": digest, "provider": "actions", "api_version": api_version(config),
              "initialization": "partial",
              "credential_guide_command": ["python3", str(Path(__file__).resolve().with_name("plane_workflow.py")),
                                           "credential-guide", "--repo", str(root), "--step", "plane"],
              "next_step": "先检查 Secret；缺少时通过 credential-guide 从 Plane PAT 创建开始分步引导，再打开当前仓库 GitHub Secret 页面。已有 Secret 则复用，之后继续默认分支激活和连接检查。"}
    if apply:
        with configuration_lock(root) as metadata:
            for name, value in before.items():
                require(snapshot(root / name)[1] == value, "Sync files changed since the plan. Inspect and retry.")
            if conflicts:
                backup_dir = metadata / "sync-backups" / (digest + "-" + uuid.uuid4().hex)
                backup_dir.mkdir(parents=True)
                for name in conflicts:
                    destination = backup_dir / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    atomic_write(destination, (root / name).read_bytes())
                result["backup"] = str(backup_dir)
            for name in changes:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(path, files[name])
    return result


def config_digest(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def native_evidence_path(root):
    from plane_workflow import run
    common = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip())
    return common / "plane-devflow" / "native-verification.json"


def validate_native_evidence(config, evidence):
    require(sync_provider(config) == "native", "Native verification requires native provider mode.")
    require(isinstance(evidence, dict) and evidence.get("config_sha256") == config_digest(config) and
            evidence.get("workspace") == config["plane"]["workspace"] and
            evidence.get("project_id") == config["plane"]["project_id"] and
            evidence.get("repository", "").lower() == config["github"]["repository"].lower(),
            "Native evidence does not match this exact configuration.")
    require(evidence.get("repository_mapped") is True and evidence.get("workflow_rules_verified") is True and evidence.get("overlapping_actions_disabled") is True and
            evidence.get("source") in {"plane_ui", "user_confirmation"},
            "Verify the actual native repository/project mapping and rules; a paid plan alone is insufficient.")
    try:
        observed = datetime.fromisoformat(evidence["observed_at"])
        require(observed.tzinfo is not None and observed <= datetime.now(timezone.utc), "Invalid native observation time.")
    except (KeyError, ValueError, TypeError):
        raise WorkflowError("Provide the native observation time with its timezone.") from None
    return evidence


def record_native(root, evidence_file, *, apply=False):
    from plane_workflow import repo_config, configuration_lock, atomic_write
    root, config = repo_config(root)
    evidence = validate_native_evidence(config, json.loads(Path(evidence_file).read_text()))
    result = {"status": "recorded" if apply else "planned", "provider": "native",
              "config_sha256": config_digest(config), "source": evidence["source"],
              "verification_limit": "记录 UI 观察或用户确认，不是通过 Plane API 自动检测官方集成。"}
    if apply:
        with configuration_lock(root):
            require(repo_config(root)[1] == config, "Configuration changed during native verification.")
            atomic_write(native_evidence_path(root), (json.dumps(evidence, indent=2) + "\n").encode())
    return result


def assess(config, *, local_files=False, online=None):
    """Derive readiness from evidence; file/Secret presence alone is insufficient."""
    online = online or {}
    if sync_provider(config) == "native":
        complete = online.get("native_mapping_verified") is True
        return {"required": True, "provider": "native", "initialization": "complete" if complete else "partial",
                "github_sync": "ready" if complete else "not_ready", "local_files_prepared": False,
                "checks": {"native_mapping_verified": online.get("native_mapping_verified")},
                "state_sync": False, "state_owner": "native", "secret_required": False,
                "message": "原生映射和规则已核对。" if complete else "需核对原生集成的仓库／项目映射和状态规则。",
                "impact": None if complete else "尚不能确认官方集成会回写此项目；插件不重复处理 PR 事件。",
                "resume": "检查官方集成后记录原生验证凭据。",
                "state_note": "PR 生命周期状态由官方集成管理；本地规则只在 Actions 模式使用。"}
    required = ("actions_enabled", "workflow_active", "sync_bundle_verified", "remote_config_matches",
                "secret_present", "connection_verified")
    checks = {key: online.get(key) for key in (*required, "remote_files_match")}
    complete = all(checks[key] is True for key in required)
    missing = any(checks[key] is False for key in
                  ("actions_enabled", "workflow_active", "sync_bundle_verified", "remote_config_matches", "secret_present"))
    bundle = online.get("sync_bundle") or inspect_bundle({}, config)
    notice = None
    if bundle["status"] == "update_available":
        notice = (f"同步包 {bundle['installed_version']} 可升级至当前插件已知版本 {bundle['latest_known_version']}；"
                  "现有版本兼容，可继续当前任务。升级需单独授权。")
    elif bundle["status"] == "upgrade_required":
        notice = "已识别的同步包不满足当前兼容性或支持策略；请单独审阅升级，保留现有配置和授权。"
    elif bundle["status"] == "unrecognized":
        notice = "同步包文件不属于插件已知的发布包；需核对现有修改，不自动覆盖。"
    return {"required": True, "provider": "actions", "secret_required": True, "initialization": "complete" if complete else "partial",
            "github_sync": "ready" if complete else "not_ready",
            "local_files_prepared": local_files, "checks": checks,
            "state_sync": state_sync_enabled(config),
            "credential_step": "plane" if checks["secret_present"] is False else None,
            "event_run_observed": online.get("event_run_observed", False),
            "sync_bundle": bundle, "sync_bundle_notice": notice,
            "message": "GitHub 后台同步已就绪。" if complete else "初始化尚未完成：GitHub 后台同步未就绪。",
            "impact": None if complete else IMPACT if missing else
                "GitHub 后台同步尚未通过验证，不能确认 PR 事件能回写 Plane。暂时需要回到 Codex 检查并同步。",
            "resume": "再次选择 Plane: 初始化，继续配置 GitHub 后台同步。",
            "state_note": None if state_sync_enabled(config) else
                "当前任务状态同步关闭：后台仅回写 PR 记录，保留任务状态；自定义状态规则尚未实现。"}


def _github_timestamp(value):
    require(isinstance(value, str), "Invalid GitHub timestamp.")
    # Python 3.10 fromisoformat requires an explicit UTC offset instead of Z.
    timestamp = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    require(timestamp.tzinfo is not None, "GitHub timestamps require a timezone.")
    return timestamp


def check(root, *, native_evidence_file=None):
    from plane_workflow import repo_config, run
    root, config = repo_config(root)
    repo = config["github"]["repository"]
    if sync_provider(config) == "native":
        evidence, errors = {}, []
        try:
            record = json.loads(Path(native_evidence_file or native_evidence_path(root)).read_text())
            validate_native_evidence(config, record)
            evidence = {"native_mapping_verified": True, "source": record["source"], "observed_at": record["observed_at"]}
        except (WorkflowError, OSError, ValueError, TypeError) as error:
            evidence["native_mapping_verified"] = False
            errors.append(str(error))
        result = assess(config, online=evidence)
        result.update(evidence=evidence, errors=errors, native_config_sha256=config_digest(config),
                      verification_limit="依据记录的 UI 观察或用户确认；配置变化会失效，官方集成变更后需重新核对。")
        return result
    expected = bundled_files()
    evidence, errors, issues = {}, [], []

    from setup_errors import ProbeError, github_json, issue

    def failed(error, stage):
        problem = error.issue if isinstance(error, ProbeError) else issue("invalid_response", stage)
        issues.append(problem)
        errors.append(problem["code"] + ": " + problem["next_action"])

    def api(path):
        return github_json(["gh", "api", f"repos/{repo}/{path}"], root, path.split("?")[0])

    try:
        metadata = github_json(["gh", "api", f"repos/{repo}"], root, "repository")
        default = metadata["default_branch"]
        require(isinstance(default, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", default), "Invalid default branch.")
        from urllib.parse import quote
        # Use one immutable default-branch snapshot for all remote file checks.
        sha = api("commits/" + quote(default, safe=""))["sha"]
        require(re.fullmatch(r"[0-9a-fA-F]{40}", sha), "Invalid GitHub default commit.")
        evidence.update(default_branch=default, default_sha=sha)
        content = lambda name: base64.b64decode(api("contents/" + name + "?ref=" + sha)["content"])
        try:
            remote = validate_config(json.loads(content(CONFIG_NAME)))
            evidence["remote_config_matches"] = remote == config
        except ProbeError as error:
            failed(error, "remote_config")
        except (WorkflowError, ValueError, KeyError, TypeError):
            evidence["remote_config_matches"] = False
        matches, remote_files = [], {}
        for name, data in expected.items():
            try:
                remote_files[name] = content(name)
                matches.append(hashlib.sha256(remote_files[name]).digest() == hashlib.sha256(data).digest())
            except ProbeError as error:
                failed(error, "remote_files")
                matches.append(None)
            except (WorkflowError, ValueError, KeyError, TypeError):
                matches.append(False)
        evidence["remote_files_match"] = False if False in matches else None if None in matches else True
        bundle = inspect_bundle(remote_files, config)
        evidence["sync_bundle"] = bundle
        evidence["sync_bundle_verified"] = (bundle["integrity_verified"] and bundle["compatible"]
                                              if bundle["integrity_verified"] is not None else None)
    except (WorkflowError, ValueError, KeyError, TypeError) as error:
        failed(error, "repository")
    for key, path, field in (("actions_enabled", "actions/permissions", "enabled"),
                             ("workflow_active", "actions/workflows/plane-devflow.yml", "state")):
        try:
            value = api(path)[field]
            require(isinstance(value, str) if key == "workflow_active" else type(value) is bool, "Invalid Actions response.")
            evidence[key] = value == "active" if key == "workflow_active" else value is True
        except (WorkflowError, ValueError, KeyError, TypeError) as error:
            failed(error, key)
    try:
        secrets = github_json(["gh", "secret", "list", "--repo", repo, "--json", "name,updatedAt"], root, "secret_metadata")
        require(isinstance(secrets, list) and all(isinstance(row, dict) and isinstance(row.get("name"), str) for row in secrets), "Invalid Secret metadata.")
        updated = next((r.get("updatedAt") for r in secrets if r["name"] == "PLANE_API_KEY"), None)
        if updated is not None:
            _github_timestamp(updated)
        evidence["secret_present"] = any(record["name"] == "PLANE_API_KEY" for record in secrets)
        evidence["secret_updated_at"] = updated
    except (WorkflowError, ValueError, KeyError, TypeError) as error:
        failed(error, "secret_metadata")
    try:
        runs = api("actions/workflows/plane-devflow.yml/runs?per_page=100")["workflow_runs"]
        require(isinstance(runs, list) and all(isinstance(row, dict) for row in runs), "Invalid workflow runs.")
        current_runs = [r for r in runs if r.get("head_sha") == evidence.get("default_sha") and
                        r.get("head_branch") == evidence.get("default_branch")]
        dispatches = sorted((r for r in current_runs if r.get("event") == "workflow_dispatch"),
                            key=lambda r: (r["id"], r.get("run_attempt", 1)), reverse=True)
        latest = dispatches[0] if dispatches else {}
        checked = latest.get("run_started_at")
        updated = evidence.get("secret_updated_at")
        fresh_secret = bool(checked and updated and _github_timestamp(checked) >= _github_timestamp(updated))
        if evidence.get("default_sha") and "secret_present" in evidence:
            evidence["connection_verified"] = latest.get("conclusion") == "success" and fresh_secret
        run_url = latest.get("html_url")
        if isinstance(run_url, str) and re.fullmatch(r"https://github\.com/" + re.escape(repo) + r"/actions/runs/[0-9]+", run_url):
            evidence["connection_run"] = run_url
        evidence["connection_conclusion"] = latest.get("conclusion") if latest.get("conclusion") in {"success", "failure", "cancelled", "timed_out", "action_required"} else None
        # PR-target run metadata describes the PR head, not the trusted checkout SHA.
        # The endpoint already scopes runs to this repository's sync workflow. This
        # observes an event only; it does not certify its checkout or Plane writes.
        evidence["event_run_observed"] = any(r.get("event") == "pull_request_target" and
                                                  r.get("conclusion") == "success" for r in runs)
    except (WorkflowError, ValueError, KeyError, TypeError) as error:
        failed(error, "connection")
    local_files = {name: (root / name).read_bytes() if (root / name).is_file() else None for name in expected}
    local_bundle = inspect_bundle(local_files, config)
    local = local_bundle["integrity_verified"] is True and local_bundle["compatible"] is True
    result = assess(config, local_files=local, online=evidence)
    result["local_sync_bundle"] = local_bundle
    result.update(evidence=evidence, errors=errors, issues=issues)
    result["verification_limit"] = "连接验证只读取项目和状态；PR 事件策略及实际写入结果仍需分别核对。"
    return result
