# Install, update and remove

[English README](../README.md) · [中文说明](../README.zh-CN.md)

## Install with Skills CLI

```sh
npx skills add SoaringLabs/plane-devflow \
  --skill plane-setup plane-start plane-deliver
```

Run the command from the target repository root. Choose Codex, Claude Code, Cursor or OpenCode when prompted. Optional `--agent codex`, `--agent claude-code`, `--agent cursor` or `--agent opencode` targets a host explicitly. The default installs into the current project. Add `--global` only when you choose user-level installation across projects. The default command remains interactive so existing-file decisions are visible. For one skill, use `--skill plane-setup` (or another entry point). Each generated skill is self-contained; its bundled fallback guides cover related workflows even when a companion skill is absent.

Requirements: Node.js 22.20+ for Skills CLI, npm, Git and an agent with local shell and MCP support. Runtime helpers use Python 3.10+; PR operations need an authenticated GitHub CLI. Skills CLI is a third-party installer, not an official Codex marketplace listing. It fetches the selected GitHub source; Plane DevFlow does not need a separate npm publication for this path.

The repository's generated `skills/` directories include instructions, UI/dependency metadata, standard-library Python helpers, references, license and distribution metadata. Their canonical sources remain under `plugins/plane-devflow/` plus standalone MCP guidance under `scripts/standalone-resources/`. Generation rewrites paths and invocation names, and CI rejects drift. Installation does not require this source checkout at runtime.

## Plane MCP connection

Open a new session in the business repository and load/request `plane-setup`. Follow only the active host's [integration guide](agent-compatibility.md). Skills CLI installs files, while MCP configuration and account consent use the host's native mechanisms. `agents/openai.yaml` is Codex-specific optional metadata, not a cross-agent MCP installer.

Reuse the host's working Plane tools and authorization. Check existing servers and the intended project/user configuration scope before adding a connection. Merge only the absent entry, preserve unrelated settings and credentials, and resolve conflicting server URLs before editing. Project configuration files are repository artifacts subject to the existing ownership/file-scope checks. User-level skill installation does not automatically choose MCP configuration scope.

The host guides cover Codex CLI registration/login, Claude Code HTTP MCP registration and `/mcp`, Cursor's JSON/UI connection and OpenCode's remote server/auth commands. The user completes browser consent. Authorization tied to one client or server identity is not copied to another agent. Reopen/refresh the session when needed, inspect actual tool schemas and retrieve the requested workspace before claiming live access. An HTTP 401 challenge alone does not establish access.

The Python/Git workflow keeps the same `.plane-devflow.json`, task receipts, branch-prefix defaults, sync scripts and PR markers across agents. `doctor` may report optional `codex_cli` availability; another host can work with it false. Hosts without managed-worktree APIs use the existing Git preparation path. Local terminal access is required for implementation; a text-only host can discuss the task but cannot execute the helpers.

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

For an existing global installation, use `--global` instead of `--project` when updating, and add `--global` when removing. Changing the recommended command does not migrate or remove existing global installations. Removing skills preserves MCP connections and credentials, business `.plane-devflow.json`, copied workflows/scripts, task worktrees and external integration settings. Background synchronization remains controlled by that repository or official integration.

## Install the Codex plugin locally

From a local checkout, register this repository and install its plugin:

```sh
codex plugin marketplace add /absolute/path/to/plane-devflow
codex plugin add plane-devflow@plane-devflow
```

The plugin bundles its three skills and the Plane MCP connection. Use `$plane-devflow:plane-setup`, `$plane-devflow:plane-start` and `$plane-devflow:plane-deliver`. Keep one active distribution to avoid duplicate skill entries. Account consent is handled by the host.

The local npm installer can also be run from the checkout after `npm ci`:

```sh
node bin/plane-devflow.mjs
node bin/plane-devflow.mjs --check
```

It requires Node.js 20+ and a plugin-enabled Codex CLI on PATH. It saves a persistent source outside the npm cache, verifies the full payload and native skill discovery, and preserves the selected source and unrelated settings. The `plane-devflow` npm package has not been published; these local commands do not publish it.

Remove the plugin with `codex plugin remove plane-devflow@plane-devflow`. Remove its source registration separately with `codex plugin marketplace remove plane-devflow`. Business configuration, task workspaces and account credentials are separate from plugin files.

## Validation scope

For an unpublished candidate, run actual Skills CLI against an isolated local Git snapshot or directory containing that candidate. The public GitHub command still resolves published source and cannot establish unpublished behavior. Validate project/global scope, selected/all skills, repeated installation, removal of source/cache, actual native discovery, helper startup and dependency parsing. Keep real user state inaccessible and test credentials empty.

See [Skills CLI commands](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), [OpenAI skill dependencies](https://developers.openai.com/plugins/build/skills#connect-skills-to-mcp-tools), the [standalone validation record](validation-skills-add.md) and the historical [npm installation validation](validation-npx.md).
