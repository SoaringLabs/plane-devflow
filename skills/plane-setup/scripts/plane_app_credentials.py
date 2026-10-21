"""Explicit macOS Plane Cloud credential creation. Secret values stay in-process.

No import-time profile/vault/network access. Plans never read a browser session.
The desktop cookie format and Cloud web endpoint are compatibility boundaries,
not a public credential-management API or a generic authenticated HTTP proxy.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile
import urllib.error
import urllib.request
from urllib.parse import quote
import uuid

from credential_store import Scope, open_store, validate_token
from plane_sync import WorkflowError, require, sync_provider

API = "https://api.plane.so"
APP = "https://app.plane.so"
TOKENS = "/api/users/api-tokens/"
MAX_RESPONSE = 256 * 1024
RECOVERY = {
    "login_required": "请先打开 Plane App，登录对应账户；完成后继续同一个操作。",
    "account_mismatch": "Plane App 登录账户与目标账户不一致；切换到对应账户后继续。",
    "permission_denied": "核对账户和目标项目权限；不要重新生成 PAT。",
    "network_unavailable": "网络恢复后继续同一个操作；创建结果不明确时先核对。",
    "rate_limited": "遵守服务的重试时间，稍后继续同一个操作。",
    "session_unavailable": "无法安全读取 Plane App 会话；检查应用存储格式或使用手动方式。",
    "unsupported": "此自动路径只支持 macOS Plane Cloud；其他环境使用手动凭据方式。",
    "keychain_unavailable": "解锁或修复钥匙串访问权限后继续；不使用明文文件保存。",
    "existing_credential": "已有本地凭据；先复用验证，只有明确授权替换时才使用 --replace。",
    "operation_in_progress": "同一账户有操作正在执行；结束后继续，勿另建操作重复创建。",
    "creation_unconfirmed": "创建可能已发生；继续同一个操作核对元数据，勿自动重发创建请求。",
    "created_without_local_copy": "PAT 已创建但本机没有可恢复副本；按显示的 PAT ID/名称处理，勿自动再生成。",
    "invalid_response": "服务响应或会话格式无法验证；保留进度，检查兼容性后继续。",
    "mapping_changed": "项目配置已变化；核对目标后重新规划，勿继续原操作。",
    "invalid_operation": "操作参数或进度无效；核对原操作，勿自动新建替代操作。",
    "expired": "所选有效期或测试凭据已到期；需要新的明确授权和有效期。",
    "credential_invalid": "PAT 无效、已过期或已撤销；先诊断，不自动生成替代凭据。",
}


class CredentialError(WorkflowError):
    def __init__(self, code):
        self.code = code
        super().__init__(RECOVERY[code])


def fail(code):
    raise CredentialError(code)


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            fail("invalid_operation")
        return parsed.astimezone(timezone.utc)
    except (AttributeError, ValueError, TypeError):
        fail("invalid_operation")


def identifier(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        fail("invalid_response")


def account_matches(identity, account):
    return isinstance(identity, dict) and any(
        isinstance(identity.get(key), str) and identity[key].casefold() == account.casefold()
        for key in ("id", "email"))


def expiry_matches(actual, expected):
    try:
        return abs((timestamp(actual) - timestamp(expected)).total_seconds()) <= 1
    except CredentialError:
        return False


@contextmanager
def app_session():
    """Read only the two Cloud auth cookies, including committed WAL contents.

    Read transactions use SQLite's normal locking, not immutable=1 (which can
    ignore a live WAL). No database backup or cookie file is made. Encrypted
    formats are deliberately unsupported rather than decrypted implicitly.
    """
    if sys.platform != "darwin":
        fail("unsupported")
    root = Path.home() / "Library/Application Support/Plane"
    candidates = [root / "Cookies", root / "Network/Cookies"]
    try:
        paths = [p for p in candidates if p.is_file()]
    except OSError:
        fail("session_unavailable")
    if not paths:
        fail("login_required")
    if len(paths) != 1 or any(p.is_symlink() for p in (root, paths[0], paths[0].parent)):
        fail("session_unavailable")
    rows, cookies = [], {}
    try:
        db = sqlite3.connect(paths[0].as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            # Never select unrelated analytics cookies or encrypted blobs.
            rows = db.execute(
                "SELECT name,value,length(encrypted_value),expires_utc,has_expires "
                "FROM cookies WHERE host_key IN ('.plane.so','plane.so','api.plane.so') "
                "AND path='/' AND name IN ('session-id','csrftoken')").fetchall()
        finally:
            db.close()
        chrome_now = (utcnow() - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 1_000_000
        for name, value, encrypted_size, expiry, has_expiry in rows:
            if has_expiry and expiry <= chrome_now:
                continue
            if encrypted_size or name in cookies:
                fail("session_unavailable")
            if not isinstance(value, str) or not 0 < len(value) <= 8192 or any(
                    not 33 <= ord(c) <= 126 or c in ";\r\n" for c in value):
                fail("session_unavailable")
            cookies[name] = value
        if "session-id" not in cookies:
            fail("login_required")
    except (sqlite3.Error, OSError, ValueError, TypeError):
        rows.clear()
        cookies.clear()
        fail("session_unavailable")
    try:
        yield cookies
    finally:
        rows.clear()
        cookies.clear()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CloudClient:
    def __init__(self, cookies):
        self.cookies = cookies
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, method, path, *, payload=None, token=None):
        session = token is None
        allowed = ((method == "GET" and path in ("/api/users/me/", TOKENS)) or
                   (method == "POST" and path == TOKENS)) if session else (
            method == "GET" and (path == "/api/v1/users/me/" or
            re.fullmatch(r"/api/v1/workspaces/[A-Za-z0-9_-]+/projects/[0-9a-f-]{36}/", path)))
        if not allowed:
            fail("unsupported")
        headers = {"Accept": "application/json", "User-Agent": "PlaneDevFlow/credential-session"}
        if session:
            headers.update(Cookie="; ".join(k + "=" + v for k, v in self.cookies.items()),
                           Origin=APP, Referer=APP + "/")
            if "csrftoken" in self.cookies:
                headers["X-CSRFToken"] = self.cookies["csrftoken"]
        else:
            headers["X-API-Key"] = validate_token(token)
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        request = urllib.request.Request(API + path, data=body, headers=headers, method=method)
        raw = None
        try:
            with self.opener.open(request, timeout=20) as response:
                if response.status != (201 if method == "POST" else 200):
                    fail("invalid_response")
                raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                fail("invalid_response")
            return json.loads(raw)
        except urllib.error.HTTPError as error:
            status = error.code
            # HTTPError owns a response stream. Its finalizer can otherwise emit
            # ResourceWarning containing the original (potentially secret) repr.
            error.close()
            if status == 401:
                fail("login_required" if session else "credential_invalid")
            if status == 403:
                fail("permission_denied")
            if status == 429:
                fail("rate_limited")
            if status >= 500:
                fail("network_unavailable")
            fail("invalid_response")
        except (ValueError, UnicodeError):
            fail("invalid_response")
        except (OSError, urllib.error.URLError):
            fail("network_unavailable")
        finally:
            headers.clear()
            request = body = raw = None

    def identity(self):
        return self.request("GET", "/api/users/me/")

    def tokens(self):
        result = self.request("GET", TOKENS)
        if not isinstance(result, list) or not all(isinstance(row, dict) for row in result):
            fail("invalid_response")
        return result

    def create(self, label, expiry):
        return self.request("POST", TOKENS, payload={"label": label, "expired_at": expiry,
            "description": "Plane DevFlow local runner credential; explicitly authorized creation."})

    def verify(self, token, scope, project_id):
        if not account_matches(self.request("GET", "/api/v1/users/me/", token=token), scope.account):
            fail("account_mismatch")
        path = "/api/v1/workspaces/" + quote(scope.workspace, safe="") + "/projects/" + project_id + "/"
        project = self.request("GET", path, token=token)
        if not isinstance(project, dict) or project.get("id") != project_id:
            fail("permission_denied")


@dataclass(frozen=True)
class PendingScope(Scope):
    operation_id: str

    @property
    def key(self):
        return super().key + ":pending:" + self.operation_id


def operation_directory():
    return Path.home() / "Library/Application Support/Plane DevFlow/credential-operations"


@contextmanager
def operation_lock(directory, scope):
    """Account/workspace lock shared by repositories; OS releases it on exit."""
    import fcntl
    for path in (directory.parent, directory):
        if path.is_symlink():
            fail("invalid_operation")
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.is_dir() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
            fail("invalid_operation")
    lock = directory / (scope.key.split(":", 1)[1] + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError:
        fail("invalid_operation")
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            fail("invalid_operation")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("operation_in_progress")
        yield
    finally:
        os.close(descriptor)


def load_receipt(path, binding):
    if not path.exists() and not path.is_symlink():
        return None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 8192:
                fail("invalid_operation")
            data = json.load(stream)
        # Return only the local schema, never arbitrary persisted fields.
        if not isinstance(data, dict) or set(data) != {
                "version", "binding", "phase", "post_attempted", "pat_id", "pending_saved",
                "target_saved", "verified_at", "expires_at", "expiry_verified"} or data["version"] != 1 or (
                    binding is not None and data["binding"] != binding):
            fail("invalid_operation")
        if not isinstance(data["binding"], str) or not re.fullmatch(r"[a-f0-9]{64}", data["binding"]):
            fail("invalid_operation")
        if data["pat_id"] is not None:
            data["pat_id"] = identifier(data["pat_id"])
        if data["phase"] not in {"preflight", "creating", "created", "pending_saved", "verified", "promoting"}:
            fail("invalid_operation")
        if any(type(data[k]) is not bool for k in ("post_attempted", "pending_saved", "target_saved", "expiry_verified")):
            fail("invalid_operation")
        timestamp(data["expires_at"])
        if data["verified_at"] is not None:
            timestamp(data["verified_at"])
        return data
    except (OSError, ValueError, TypeError, KeyError):
        fail("invalid_operation")


def save_receipt(path, receipt):
    if path.is_symlink():
        fail("invalid_operation")
    descriptor, temporary = tempfile.mkstemp(prefix=".credential-operation-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(receipt, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def create(path, *, account, expires_at, operation_id=None, expected_config_sha256=None, replace=False, apply=False):
    """Plan/apply a single authorized operation; never silently mint on retry."""
    from plane_workflow import repo_config
    root, config = repo_config(path)
    scope = Scope.from_config(config, account)
    config_digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    if apply and expected_config_sha256 != config_digest:
        fail("mapping_changed")
    if sync_provider(config) != "actions" or sys.platform != "darwin" or (
            scope.api_url != API or config["plane"]["app_url"].rstrip("/").lower() != APP):
        fail("unsupported")
    project_id = identifier(config["plane"]["project_id"])
    if not re.fullmatch(r"[A-Za-z0-9_-]+", scope.workspace) or "plane_api_" in scope.account:
        fail("invalid_operation")
    expiry = timestamp(expires_at).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if not apply and timestamp(expiry) <= utcnow():
        fail("expired")
    if apply and operation_id is None:
        fail("invalid_operation")
    operation_id = identifier(operation_id or uuid.uuid4())
    label = "Plane DevFlow: " + scope.workspace[:60] + " [" + operation_id + "]"
    binding = hashlib.sha256(json.dumps([scope.metadata(), config_digest, project_id, label, expiry, replace],
                                        sort_keys=True).encode()).hexdigest()
    result = {"status": "planned", "source": "plane_app_session", "operation_id": operation_id,
              "account": scope.account, "workspace": scope.workspace, "project_id": project_id,
              "pat_label": label, "expires_at": expiry, "pat_id": None,
              "keychain_account": scope.key, "keychain_service": "plane-devflow",
              "replace": replace, "writes_performed": False, "pat_created": False,
              "pending_saved": False, "keychain_saved": False, "verified": False,
              "credential_value_returned": False, "permissions": "full_owner_permissions"}
    result["config_sha256"] = config_digest
    if not apply:
        result["apply_command"] = [sys.executable, str(Path(__file__).with_name("plane_workflow.py")),
            "credential-create", "--repo", str(root), "--account", scope.account, "--expires-at", expiry,
            "--operation-id", operation_id, "--expected-config-sha256", config_digest,
            *(["--replace"] if replace else []), "--apply"]
        return result
    directory = operation_directory()
    scope_prefix = scope.key.split(":", 1)[1] + "-"
    receipt_path = directory / (scope_prefix + operation_id + ".json")
    result["receipt_path"] = str(receipt_path)
    record = None
    stage = "preflight"
    token = stored = target_value = data = None
    try:
        with operation_lock(directory, scope):
            record = load_receipt(receipt_path, binding) or {
                "version": 1, "binding": binding, "phase": "preflight", "post_attempted": False,
                "pat_id": None, "pending_saved": False, "target_saved": False, "verified_at": None,
                "expires_at": expiry, "expiry_verified": False}
            if record["phase"] == "verified":
                result.update(status="already_completed", pat_id=record["pat_id"],
                              previously_verified_at=record["verified_at"], next_step="verify_saved_credential")
                try:
                    leftover = open_store(PendingScope(scope.api_url, scope.workspace, scope.account, operation_id))
                    if leftover.contains():
                        leftover.delete(interactive=False)
                    result["pending_cleanup"] = "removed"
                except Exception:
                    result["pending_cleanup"] = "retry_required"
                return result
            if timestamp(expiry) <= utcnow():
                fail("expired")
            # A new operation must not bypass another unfinished creation for this scope.
            for other in directory.glob("*.json"):
                if other == receipt_path:
                    continue
                try:
                    if other.is_symlink():
                        fail("invalid_operation")
                    if other.name.startswith(scope_prefix):
                        previous = load_receipt(other, None)
                        expired = previous["expiry_verified"] and timestamp(previous["expires_at"]) <= utcnow()
                        if previous["phase"] != "verified" and not expired:
                            fail("operation_in_progress")
                except OSError:
                    fail("invalid_operation")
            stage = "keychain_preflight"
            store = open_store(scope)
            pending = open_store(PendingScope(scope.api_url, scope.workspace, scope.account, operation_id))
            pending_exists = pending.contains()
            if pending_exists and not record["post_attempted"]:
                fail("invalid_operation")
            if not record["post_attempted"] and not pending_exists and store.contains() and not replace:
                fail("existing_credential")
            stage = "load_session"
            with app_session() as cookies:
                client = CloudClient(cookies)
                stage = "session_identity"
                identity = client.identity()
                if not account_matches(identity, scope.account):
                    fail("account_mismatch")
                identity = None
                if not pending_exists:
                    if record["post_attempted"]:
                        stage = "reconcile_creation"
                        matching = [r for r in client.tokens() if r.get("label") == label]
                        if len(matching) == 1:
                            record["pat_id"] = identifier(matching[0].get("id"))
                            save_receipt(receipt_path, record)
                            fail("created_without_local_copy")
                        fail("creation_unconfirmed")
                    if repo_config(root)[1] != config:
                        fail("mapping_changed")
                    stage = "create_pat"
                    record.update(phase="creating", post_attempted=True)
                    save_receipt(receipt_path, record)
                    result["writes_performed"] = True
                    data = client.create(label, expiry)
                    if not isinstance(data, dict):
                        fail("invalid_response")
                    token = validate_token(data.pop("token", None))
                    record.update(phase="created", pat_id=identifier(data.get("id")))
                    result["pat_created"] = True
                    stage = "save_pending"
                    pending.save(token, replace=False, interactive=False)
                    record.update(phase="pending_saved", pending_saved=True)
                    save_receipt(receipt_path, record)
                    # Verify server-applied expiry before replacing the selected destination.
                    if not expiry_matches(data.get("expired_at"), expiry):
                        fail("invalid_response")
                    record["expiry_verified"] = True
                    save_receipt(receipt_path, record)
                    data = None
                else:
                    # A previous response may have been interrupted before expiry verification.
                    stage = "verify_server_metadata"
                    metadata = [r for r in client.tokens() if r.get("label") == label and r.get("id") == record["pat_id"]]
                    if len(metadata) != 1 or not expiry_matches(metadata[0].get("expired_at"), expiry):
                        fail("invalid_response")
                    record.update(pending_saved=True, expiry_verified=True)
                    save_receipt(receipt_path, record)
                stage = "verify_pending"
                stored = pending.read(interactive=False)
                if token is not None and not hmac.compare_digest(token, stored):
                    fail("invalid_response")
                token = None
                client.verify(stored, scope, project_id)
                if repo_config(root)[1] != config:
                    fail("mapping_changed")
                stage = "save_target"
                record["phase"] = "promoting"
                save_receipt(receipt_path, record)
                # Recover a crash after an atomic target save by comparing it to the pending copy.
                if store.contains():
                    target_value = store.read(interactive=False)
                same = target_value is not None and hmac.compare_digest(target_value, stored)
                if not same:
                    if target_value is not None and not replace:
                        fail("existing_credential")
                    store.save(stored, replace=replace, interactive=False)
                record["target_saved"] = True
                save_receipt(receipt_path, record)
                stage = "verify_target"
                target_value = store.read(interactive=False)
                if not hmac.compare_digest(target_value, stored):
                    fail("invalid_response")
                client.verify(target_value, scope, project_id)
                record.update(phase="verified", verified_at=utcnow().isoformat())
                save_receipt(receipt_path, record)
                result.update(status="verified", keychain_saved=True, verified=True,
                              writes_performed=True, next_step="local_credential_ready")
                stage = "cleanup_pending"
                try:
                    pending.delete(interactive=False)
                    result["pending_cleanup"] = "removed"
                except Exception:
                    result["pending_cleanup"] = "retry_required"
    except CredentialError as error:
        code = error.code
        if stage == "create_pat" and record and record["post_attempted"]:
            if code in {"login_required", "permission_denied", "rate_limited"}:
                # A definite rejected request can be retried after fixing its cause.
                record.update(phase="preflight", post_attempted=False)
                save_receipt(receipt_path, record)
            else:
                code = "creation_unconfirmed"
        result.update(status=code, failed_stage=stage, next_action=RECOVERY[code])
    except Exception:
        code = "creation_unconfirmed" if stage == "create_pat" else (
            "keychain_unavailable" if stage in {"keychain_preflight", "save_pending", "verify_pending",
                                              "save_target", "verify_target"} else "invalid_response")
        result.update(status=code, failed_stage=stage, next_action=RECOVERY[code])
    finally:
        token = stored = target_value = data = None
    if record:
        result.update(pat_id=record["pat_id"], pending_saved=record["pending_saved"],
                      keychain_saved=record["target_saved"], creation_attempted=record["post_attempted"])
    return result
