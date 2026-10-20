# Install, update, migrate and remove

[English README](../README.md) · [中文说明](../README.zh-CN.md)

## Install with Skills CLI

```sh
npx skills add SoaringLabs/plane-for-codex \
  --skill plane-setup plane-start plane-deliver
```

Run the command from the target repository root. Choose Codex, Claude Code, Cursor or OpenCode when prompted. Optional `--agent codex`, `--agent claude-code`, `--agent cursor` or `--agent opencode` targets a host explicitly. The default installs into the current project. Add `--global` only when you choose user-level installation across projects. The default command remains interactive so existing-file decisions are visible. For one skill, use `--skill plane-setup` (or another entry point). Each generated skill is self-contained; its bundled fallback guides cover related workflows even when a companion skill is absent.

Requirements: Node.js 22.20+ for Skills CLI, npm, Git and an agent with local shell and MCP support. Runtime helpers use Python 3.10+; PR operations need an authenticated GitHub CLI. Skills CLI is a third-party installer, not an official Codex marketplace listing. It fetches the selected GitHub source; Plane for Codex does not need a separate npm publication for this path.

The repository's generated `skills/` directories include instructions, UI/dependency metadata, standard-library Python helpers, references, license and distribution metadata. Their canonical sources remain under `plugins/plane-for-codex/` plus standalone MCP guidance under `scripts/standalone-resources/`. Generation rewrites paths and invocation names, and CI rejects drift. Installation does not require this source checkout at runtime.

## Plane MCP connection

Open a new session in the business repository and load/request `plane-setup`. Follow only the active host's [integration guide](agent-compatibility.md). Skills CLI installs files, while MCP configuration and account consent use the host's native mechanisms. `agents/openai.yaml` is Codex-specific optional metadata, not a cross-agent MCP installer.

Reuse the host's working Plane tools and authorization. Check existing servers and the intended project/user configuration scope before adding a connection. Merge only the absent entry, preserve unrelated settings and credentials, and resolve conflicting server URLs before editing. Project configuration files are repository artifacts subject to the existing ownership/file-scope checks. User-level skill installation does not automatically choose MCP configuration scope.

The host guides cover Codex CLI registration/login, Claude Code HTTP MCP registration and `/mcp`, Cursor's JSON/UI connection and OpenCode's remote server/auth commands. The user completes browser consent. Authorization tied to one client or server identity is not copied to another agent. Reopen/refresh the session when needed, inspect actual tool schemas and retrieve the requested workspace before claiming live access. An HTTP 401 challenge alone does not establish access.

The Python/Git workflow keeps the same `.plane-for-codex.json`, task receipts, branch-prefix defaults, sync scripts and PR markers across agents. `doctor` may report optional `codex_cli` availability; another host can work with it false. Hosts without managed-worktree APIs use the existing Git preparation path. Local terminal access is required for implementation; a text-only host can discuss the task but cannot execute the helpers.

## Update or remove standalone skills

Rerun the installation command to refresh the selected skills from their source. For installations with GitHub tracking metadata, Skills CLI also supports:

```sh
npx skills check
npx skills update plane-setup plane-start plane-deliver --project
```

Local directories and file-based test sources may not create GitHub update-tracking records; a zero exit code with no tracked skills is not a successful update check. Reinstall from that source to refresh it. Public GitHub update tracking for an unpublished candidate must be verified after an authorized publication.

Run these commands from the repository where the skills were installed. Reopen the agent session after updates. Remove project entries with:

```sh
npx skills remove plane-setup plane-start plane-deliver
```

For an existing global installation, use `--global` instead of `--project` when updating, and add `--global` when removing. Changing the recommended command does not migrate or remove existing global installations. Removing skills preserves MCP connections and credentials, business `.plane-for-codex.json`, copied workflows/scripts, task worktrees and external integration settings. Background synchronization remains controlled by that repository or official integration.

## Existing local marketplace installations

The complete plugin and its `$plane-for-codex:plane-setup`, `$plane-for-codex:plane-start`, `$plane-for-codex:plane-deliver` identifiers remain supported. Existing users can keep that installation; no automatic migration or authorization reset is required.

To switch deliberately, first inspect the existing plugin/MCP connection and any local customizations. Preserve its source checkout and account authorization. Install the standalone skills, then disable/remove only the duplicate plugin skill distribution when you are ready. If its Plane connection is plugin-owned, establish and verify a standalone connection before disabling that plugin; OAuth bound to a different connection identity may require user login. Keep one active distribution to avoid duplicate entries. Skill removal and credential removal are separate operations; do not delete shared account credentials to tidy up the menu.

The default Skills CLI command does not replace marketplace registrations. Existing business mappings, worktree receipts, native/basic/legacy state rules and copied Actions files retain their own update policy.

## Complete plugin compatibility

The previously published npm 0.8.1 installer remains available as a legacy compatibility channel. The current Skills CLI/GitHub release does not require a new npm publication:

```sh
npx plane-for-codex@latest
```

It requires Node.js 20+ and a plugin-enabled Codex CLI on PATH (verified with 0.163.0). It bundles the complete plugin, saves an immutable persistent source outside the npx cache, then registers/installs through native Codex commands. It verifies the complete payload and three plugin-qualified skills. Use `npx plane-for-codex@latest --check` for a read-only check; `--json` and `--help` remain available.

Existing marketplace registrations retain their selected source. Recognized Git sources refresh the same ref; local development checkouts retain their modifications and update through the usual Git workflow. If source-type metadata is absent, the installer preserves the source and reports its actual version. Modified npm-managed payloads cause an explicit error instead of being overwritten. To change to npm-managed storage deliberately, preserve local edits and remove only the old marketplace registration before reinstalling. Keep the old checkout and shared authorization.

The native Git alternative also remains supported:

```sh
codex plugin marketplace add SoaringLabs/plane-for-codex && \
  codex plugin add plane-for-codex@plane-for-codex
```

Here marketplace means the repository catalog, not an official directory listing. Contributors may register an explicit checkout path. Preserve existing registrations instead of changing sources merely to follow another example. Remove the installed plugin with `codex plugin remove plane-for-codex@plane-for-codex`; its source registration and unrelated business data remain separate.

## Validation scope

For an unpublished candidate, run actual Skills CLI against an isolated local Git snapshot or directory containing that candidate. The public GitHub command still resolves published source and cannot establish unpublished behavior. Validate project/global scope, selected/all skills, repeated installation, removal of source/cache, actual native discovery, helper startup and dependency parsing. Keep real user state inaccessible and test credentials empty.

See [Skills CLI commands](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), [OpenAI skill dependencies](https://developers.openai.com/plugins/build/skills#connect-skills-to-mcp-tools), the [standalone validation record](validation-skills-add.md) and the historical [npm installation validation](validation-npx.md).
