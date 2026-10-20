# Agent host and execution capabilities

Read this before the first local operation or live Plane call, and when the host/tool inventory changes. Use the active session's reported host, tools and permissions; installed executables alone do not identify the current agent.

| Active host | Read only its integration guide |
| --- | --- |
| Codex | [Codex](hosts/codex.md) |
| Claude Code | [Claude Code](hosts/claude-code.md) |
| Cursor | [Cursor](hosts/cursor.md) |
| OpenCode | [OpenCode](hosts/opencode.md) |

For another/unknown host, inspect whether it can load Agent Skills, execute local Git/Python commands and connect to the Plane MCP. Ask only for a missing host identity when needed to choose configuration syntax. Missing terminal access blocks local development helpers; report that capability gap instead of inventing shell execution. Browser/app control is optional: use the existing recovery guide's manual links when absent.

Resolve helper paths from the installed skill and pass the actual target repository/recorded execution directory. Use the host's shell tool with that directory explicitly, or change directory inside each command when no cwd parameter exists. Creating a worktree does not move this session. Host-managed worktree tools are an optional enhancement; use the standard `prepare` Git worktree path when absent. Branch prefixes, `.plane-for-codex.json`, Git metadata receipts and PR comment markers retain their existing names for interoperability. A worktree/receipt shared across agents still needs the same task ownership and fresh evidence checks; installation does not transfer ownership.

Use the host's skill picker/invocation syntax. Plain `plane-setup`, `plane-start` and `plane-deliver` references name workflows, not universally valid slash/dollar commands. Cross-workflow fallback guides live in this skill so an absent companion entry point does not require a second installation. `agents/openai.yaml` is optional Codex UI/dependency metadata; other hosts use SKILL.md and their native MCP configuration. The compatibility doctor's `codex_cli` field reports availability only: false does not block another host.

Discover the current Plane tool catalog through the host and inspect schemas. MCP prefixes and function names can differ by host/server version; use the tool that performs the requested workspace/project/work-item operation rather than inventing a Codex-specific tool name. Use read-only workspace retrieval to establish current account access. Skills installation and model login grant no Plane writes, PR merges or completion authority. Preserve the existing check/plan/apply, human acceptance, credential handling and native/Actions ownership rules.
