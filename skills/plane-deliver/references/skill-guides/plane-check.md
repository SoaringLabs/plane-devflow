---
name: plane-check
description: Diagnose Plane MCP access in the agent session that is failing, especially after switching agents, chats, profiles, or worktrees. Check tool availability, authentication, the connected workspace, and optional project access with read-only probes. Use for “Plane 连不上” or “换 agent 后找不到 Plane”; use plane-setup for repository association or GitHub sync.
---

# Check Plane access

Run the check in the affected session. If the affected context is a worker or subagent, have that context perform the probe when available under the host's delegation rules and label its result separately. A successful call from a parent, another session, the browser, or a CLI does not verify the affected session.

1. **Discover tools.** Use the current session's native tool inventory, including deferred discovery, and inspect the actual Plane schema. An installed skill or configured server does not prove its tools were loaded. If no appropriate tool appears, use [host triage](../plane-check-hosts.md) and stop before attempting a different access path.
2. **Read the bound workspace.** Use the read-only workspace retrieval action (for the official Plane MCP, `workspace` with `action: retrieve` and no workspace argument). No repository or mapping is needed. Check both tool-level errors and the response body. Record the returned workspace slug and authentication mode if available. Missing optional metadata alone is not a failure.
3. **Check the expected target.** Use the user's target or the current checkout's `.plane-devflow.json` (`plane.workspace` and `plane.project_id`). Read only the needed mapping fields and report missing or invalid mappings separately. Ignore the mapped project if its workspace differs from the user’s explicit target. If the workspace differs, report both slugs and stop before the project call. If a project is identified in the matching workspace, retrieve it by ID and verify the returned identity. Use a scoped read-only project lookup if only an identifier is known and the live schema supports it. With no expected target, report that workspace access is verified and project access was not checked.

Classify the first unverified layer from the available evidence:

| Observation | Report and next step |
| --- | --- |
| Plane tool unavailable | Tool not exposed in this session. Inspect the active host's registration, permissions and session scope. Suggest opening a fresh session if registration exists but the session has not picked it up. |
| Explicit login/consent error or 401 | Authentication rejected or required. Use the affected host's connection UI or login flow as a separate user action; distinguish expired login from other failures only if the host confirms it. |
| Explicit policy denial or 403 | Access denied at the step that returned it. Check the relevant host policy, account or workspace/project permissions; a 403 alone does not identify which. |
| DNS, TLS, timeout, rate limit, or service error | Report the observed transport or service error and where it occurred. Give one relevant follow-up; keep the underlying cause unknown if evidence is ambiguous. |
| Workspace read succeeds, slug differs | Connected to a different workspace. Verify the intended target and select the correct connection in the affected host. |
| Workspace succeeds, project returns 404 or cannot be verified | Workspace access works. Check the mapping and project visibility; a 404 can mask denied access. |

Return the affected host/session or worker, the **tool → workspace → project** results (verified, failed, or not checked), a short redacted observation, and the next step. Successful reads do not verify write access or GitHub sync.

Keep this a read-only check: no install, login, reconnect, config edits, or remote writes. Do not ask for or print credentials. Report only the necessary identifiers and sanitized errors. Do not use a PAT, browser session, or another agent's result as a fallback for the affected session's live check.
