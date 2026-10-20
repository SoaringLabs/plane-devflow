# Agent compatibility

The default is a shared Agent Skills package for Codex, Claude Code, Cursor and OpenCode. The original Codex plugin, qualified identifiers and npm installer remain compatible. Repository/package names and `.plane-for-codex.json` stay stable; installing another host does not migrate accounts or business configuration.

```sh
npx skills add SoaringLabs/plane-for-codex \
  --skill plane-setup plane-start plane-deliver
```

Run from the target repository root and choose the intended host interactively. For an explicit target, append `--agent codex`, `--agent claude-code`, `--agent cursor` or `--agent opencode`. Installation defaults to the current project; optionally add `--global` for user-level reuse across projects. Each host receives the same self-contained workflow; native UI metadata is optional. Pre-release verification used an isolated source snapshot. Public-source and CI status are tracked separately in the [0.9.0 release record](validation-0.9.0.md).

## Integration guides

| Agent | Invocation and MCP guide | User skill location |
| --- | --- | --- |
| Codex | [Codex](../skills/plane-setup/references/hosts/codex.md) | `~/.agents/skills/` |
| Claude Code | [Claude Code](../skills/plane-setup/references/hosts/claude-code.md) | `~/.claude/skills/` |
| Cursor | [Cursor](../skills/plane-setup/references/hosts/cursor.md) | `~/.agents/skills/` (tested CLI), also `~/.cursor/skills/` |
| OpenCode | [OpenCode](../skills/plane-setup/references/hosts/opencode.md) | `~/.agents/skills/` (tested CLI), also `~/.config/opencode/skills/` |

See [host capabilities](../skills/plane-setup/references/host-runtime.md) for terminal/tool discovery, optional managed worktrees and plain workflow names. Use each host's native tool schema; MCP prefixes can differ. Shared Git/Python helpers run without Codex installed. PR operations require GitHub CLI access; local implementation requires terminal tools and Git/Python. Missing capabilities produce a scoped pending result.

These checks target local desktop/CLI sessions. Remote workers, SSH sessions and cloud agents need their own installation and credentials; local global scope does not imply synchronization. In particular, Cursor cloud synchronization of skills uses its Cursor-specific global directory rather than the shared directory used by the tested installer.

## Authorization and compatibility

Skill installation scope and MCP configuration scope are independent. Preserve existing server URLs/identities, credentials and unrelated settings. Merge only an absent connection into the chosen host, use that host's browser OAuth when needed and verify workspace access. OpenAI dependency metadata does not register other clients. OAuth tied to one client must not be copied into another client's store. Model-provider login is separate from Plane OAuth.

The same file-scope preflight, task binding, human acceptance and merge authorization apply across hosts. Existing branch-prefix defaults, task receipts, comment markers, copied Actions files and native/basic/legacy state ownership remain unchanged. A workflow installation does not grant extra business writes or session orchestration. Use the existing Git preparation path when host-managed worktrees are unavailable.

## Verification matrix

The 0.9.0 payload's per-agent installation, native discovery, MCP and unverified items are recorded below after actual isolated checks. File placement or an unauthenticated endpoint alone does not count as a successful native/model workflow.

Tested on macOS arm64 with Skills CLI 1.7.4, Node.js 24.15.0 and Python 3.14.3. Every host used a separate empty HOME/config/cache profile, without copying real credentials.

| Agent / native CLI | Three-skill global + project installation, repeat and removal | Native skill recognition | Native MCP configuration | Remaining checks |
| --- | --- | --- | --- | --- |
| Codex 0.163.0 | Passed; all payload bytes and helper startup verified | Passed via native `skills/list`, including English UI and dependency metadata | Passed via `codex mcp get` | Fresh-profile OAuth, model execution and business workflow |
| Claude Code 2.1.301 | Passed; all payload bytes and helper startup verified | Passed: native session init lists all three skills and slash commands; model request then stops at login | Passed via native `mcp add/get`; unrelated server retained | Model login, fresh-profile Plane OAuth and business workflow |
| Cursor Agent 2026.10.19-6bbf2c4 | Passed; all payload bytes and helper startup verified | Unverified: native session requires Cursor login before exposing a skill catalog | Earlier native list returned `requires_authentication`; public-source recheck returned connection failure twice; retained server remains | Native skill loading, model login, Plane OAuth and business workflow |
| OpenCode 1.19.3 | Passed; all payload bytes and helper startup verified | Passed via native `debug skill` | Passed via native `debug config`; `mcp list` reports Plane needs authentication and retains the other server | Model-provider login, fresh-profile Plane OAuth and business workflow |

MCP configuration recognition is not authenticated tool access. No fresh test client completed browser consent or a model-driven business operation. Cursor desktop rendering, remote/cloud runtimes and native Claude/Cursor/OpenCode clients on Windows/Linux remain unverified. Public-source installation/tracking checks and the guarded Windows Codex fixture are described in the [release record](validation-0.9.0.md); final CI status is linked in the Release. The local installer tests are not a claim of universal compatibility with every Agent Skills host.

264 Python tests, 18 compatibility installer unit tests and the Codex standalone install/refresh/removal regression passed. All 24 existing decision-eval cases passed structure validation; no new multi-host model decision scores are claimed. Canonical plugin behavior and the compatibility installer runtime are unchanged; release versions are updated together. The original local verification left the primary checkout unchanged. Real configuration/authentication hashes remained unchanged, and removal preserved synthetic host settings, MCP registrations/auth files and the business mapping. See [standalone validation](validation-skills-add.md) for detailed evidence and earlier baseline checks.

Sources: [Agent Skills](https://agentskills.io/specification), [Skills CLI supported agents](https://github.com/vercel-labs/skills/blob/main/docs/agents.md). Host-specific primary documentation is linked in each integration guide.
