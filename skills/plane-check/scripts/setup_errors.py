"""Safe, structured failures for read-only setup probes. Never echo service output."""
import json

from plane_sync import WorkflowError


RECOVERY = {
    "authentication_required": (False, "登录对应服务后继续；保留已有项目关联和其他授权。"),
    "permission_denied": (False, "核对账号、项目／仓库权限及组织 SSO；由有权限的人完成当前步骤。"),
    "not_found_or_hidden": (False, "核对目标及权限；404 也可能表示资源对当前账号不可见。"),
    "rate_limited": (True, "遵守服务的重试时间，稍后继续；不要重新创建 Token 或切换 API 版本。"),
    "network_unavailable": (True, "网络恢复后重新检查；写入请求先核对结果再重试。"),
    "cli_unavailable": (False, "使用网页完成人工步骤；自动远端验证需要可用的 GitHub CLI 或授权连接器。"),
    "invalid_response": (True, "服务返回无法验证的数据，稍后重新检查，保持状态为未知。"),
    "probe_failed": (False, "无法确认当前状态；核对服务、CLI 和账号权限后继续。"),
}


def issue(code, stage):
    retryable, action = RECOVERY[code]
    return {"code": code, "stage": stage, "retryable": retryable, "next_action": action}


class ProbeError(WorkflowError):
    def __init__(self, code, stage):
        self.issue = issue(code, stage)
        super().__init__(f"Setup probe {stage}: {code}. {self.issue['next_action']}")


def github_json(args, root, stage):
    from plane_workflow import run
    try:
        response = run(args, root, check=False)
    except WorkflowError as error:
        # run() exposes only a safe operation label, never raw stderr.
        message = str(error).lower()
        code = "network_unavailable" if "timed out" in message else "permission_denied" if "permission" in message else "cli_unavailable" if "cannot run" in message else "probe_failed"
        raise ProbeError(code, stage) from None
    if response.returncode:
        text = response.stderr.lower()
        if "429" in text or "rate limit" in text:
            code = "rate_limited"
        elif "401" in text or "gh auth login" in text or "not logged" in text:
            code = "authentication_required"
        elif "403" in text or "sso" in text or "forbidden" in text:
            code = "permission_denied"
        elif "404" in text or "not found" in text:
            code = "not_found_or_hidden"
        elif any(word in text for word in ("timeout", "timed out", "connection", "resolve host", "502", "503", "504")):
            code = "network_unavailable"
        else:
            code = "probe_failed"
        raise ProbeError(code, stage) from None
    try:
        return json.loads(response.stdout)
    except (ValueError, TypeError):
        raise ProbeError("invalid_response", stage) from None
