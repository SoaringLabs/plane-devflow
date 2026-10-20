<p align="center">
  <img src="plugins/plane-for-codex/assets/icon.png" alt="Plane for Codex logo" width="88" height="88">
</p>
<h1 align="center">Plane for Codex</h1>
<p align="center">
  <a href="https://github.com/SoaringLabs/plane-for-codex/releases"><img src="https://img.shields.io/github/v/release/SoaringLabs/plane-for-codex?color=7661d8" alt="Latest release"></a>
  <a href="https://github.com/SoaringLabs/plane-for-codex/stargazers"><img src="https://img.shields.io/github/stars/SoaringLabs/plane-for-codex?style=flat&amp;color=7661d8" alt="GitHub stars"></a>
  <a href="https://github.com/SoaringLabs/plane-for-codex/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/SoaringLabs/plane-for-codex/validate.yml?branch=main&amp;label=checks" alt="Main branch checks"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10 or newer"></a>
</p>
<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>
<p align="center"><strong>From a Plane task to a reviewed pull request.</strong><br>Independent workspaces. Connected context. A clear handoff.</p>
<p align="center"><a href="#quick-start">Quick start</a> · <a href="#features">Features</a> · <a href="#skills">Skills</a> · <a href="#documentation">Docs</a> · <a href="CHANGELOG.md">Changelog</a></p>
<p align="center"><img src="docs/assets/workflow.svg" alt="Workflow illustration: Plane task → isolated agent workspace → linked GitHub pull request. DEMO-123 is an example." width="100%"></p>

Open-source Agent Skills connecting **Plane tasks, agent development and GitHub PRs**, with integration guides for **Codex, Claude Code, Cursor and OpenCode**. Start with the task's requirements, work in its own directory, and deliver a linked PR with verification and acceptance records. No additional service to deploy.

## Quick start

### Install

Run this command in your terminal:

```sh
npx skills add SoaringLabs/plane-for-codex \
  --skill plane-setup plane-start plane-deliver \
  --global
```

Skills CLI installs three self-contained skills from GitHub and lets you choose the target agent. `--global` makes them available across projects; omit it for the current project only. To target one host directly, add `--agent codex`, `--agent claude-code`, `--agent cursor` or `--agent opencode`. Requires [Node.js 22.20+](https://nodejs.org/), npm, Git and an agent with local terminal and MCP support; runtime helpers use Python 3.10+, and PR operations need an authenticated [GitHub CLI](https://cli.github.com/).

Open a **new agent session in your target repository**, select or request **plane-setup**, and follow setup to connect Plane and choose a project. Skills installation, MCP registration, browser authorization and GitHub background synchronization are separate steps. Existing connections and authorization are reused. See [MCP setup](docs/installation.md#plane-mcp-connection) if Plane tools are missing.

Already using the complete plugin? Keep that installation and its `$plane-for-codex:plane-setup` identifiers until you choose a [migration](docs/installation.md#existing-local-marketplace-installations). Install one distribution at a time to avoid duplicate entries.

### Start your first task

`PROJECT-123` below is an example; replace it with an existing task ID.

| Step | Ask your agent | Expected result |
| --- | --- | --- |
| Connect | Use **plane-setup** | Project association and verified sync, or the precise remaining setup step |
| Develop | “Use plane-start to start PROJECT-123” | The task's own working directory, branch, requirements and acceptance scope |
| Deliver | “Use plane-deliver to deliver PROJECT-123; keep the PR open” | A linked PR, actual check results and outstanding acceptance items |

Setup's `.plane-for-codex.json` must reach the configured base branch before independent task branches are created. You can also ask to read a task and discuss it without saving files. Delivery, acceptance and merge follow the requested scope; existing authorization is reused.

## Features

| Capability | What it gives you |
| --- | --- |
| **Independent task workspaces** | A separate directory and branch for each task, preserving the primary checkout and other tasks' edits |
| **Resume the right version** | Recover the task's recorded directory and context when continuing in another chat |
| **Linked PR delivery** | Keep one primary PR tied to the task, with implementation and verification reports in Plane |
| **Test when you're ready** | Ask your agent to prepare the task version for manual testing, with a usable entry point and test steps |
| **Background GitHub sync** | Record PR events through GitHub Actions or an existing official Plane integration |
| **Clear acceptance and completion** | Keep runtime readiness, human acceptance and merge authorization separate |

To try a delivered result, say: “Run PROJECT-123 from its task workspace so I can test it.” The agent follows the project's own run/build instructions, checks the source version and hands over the entry point. PR delivery alone does not start an environment. See [acceptance handoff](skills/plane-deliver/references/acceptance-environment.md).

## Skills

Use the host's skill picker or request a workflow below. Codex uses `$plane-setup`; Claude Code uses `/plane-setup`; OpenCode loads the named skill through its native tool. See [host guides and verification status](docs/agent-compatibility.md) for syntax, MCP setup and tested limits.

| Skill | Use when |
| --- | --- |
| **Set Up Plane** | Associate a project, inspect/reconfigure the mapping, or resume sync setup — `plane-setup` |
| **Start Plane Task** | Discuss, plan, start or resume an existing task — `plane-start` |
| **Deliver Plane Task** | Deliver a PR, prepare testing, record acceptance or finalize authorized work — `plane-deliver` |

Each skill bundles its own runtime and references, so selected skills can also be installed individually. The complete plugin remains a supported alternative; its skill identifiers retain the `$plane-for-codex:` prefix.

## GitHub synchronization

| Provider | Requirements |
| --- | --- |
| **GitHub Actions** — default | A separate Plane PAT in the repository Secret `PLANE_API_KEY`, plus sync files merged into the default branch |
| **Official Plane integration** | An enabled and verified repository/project mapping and rules; no plugin workflow or PAT Secret |

Project association uses browser authorization, without a PAT. For Actions, enter the PAT directly through GitHub Secrets or a human-operated hidden terminal prompt. Keep it out of chat.

Incomplete setup is saved and resumable. **A successful connection check and a real PR-event writeback are reported separately.** New basic mappings record PR activity without changing task states; legacy mappings retain their existing rules. Native transitions belong to the official integration. See [setup and sync](skills/plane-setup/references/setup.md).

## Scope

Currently supports existing tasks, one primary PR per task, Plane Cloud and github.com. Cycle/task management, custom status rules, multi-PR aggregation, full self-hosted Plane and GitHub Enterprise support are outside the current scope.

## Update or remove

Rerun the installation command to refresh these three skills. For GitHub-tracked installations, Skills CLI also provides update checks:

```sh
npx skills check
npx skills update plane-setup plane-start plane-deliver --global
```

Use `npx skills remove plane-setup plane-start plane-deliver --global` and select the intended host to remove the global skills. Project installs use the corresponding project scope. Open a new chat after updates. Removal keeps MCP connections, account authorization, business mappings, copied workflows and task workspaces. The [installation guide](docs/installation.md) covers plugin updates and deliberate migration.

## Documentation

| Topic | Read more |
| --- | --- |
| Agent compatibility | [Codex, Claude Code, Cursor and OpenCode](docs/agent-compatibility.md) |
| Installation and updates | [Install, update, migrate and remove](docs/installation.md) |
| Setup and recovery | [Project association & sync](skills/plane-setup/references/setup.md) · [Resume setup](skills/plane-setup/references/recovery.md) |
| Development and handoff | [Task execution](skills/plane-start/references/task-execution.md) · [Parallel tasks](skills/plane-start/references/parallel-tasks.md) · [Acceptance environments](skills/plane-deliver/references/acceptance-environment.md) |
| Configuration | [Basic mapping](examples/plane-for-codex.basic.json) · [Legacy mapping](examples/plane-for-codex.example.json) |
| Contributing and releases | [Contributing](CONTRIBUTING.md) · [Architecture](docs/architecture.md) · [Publishing](PUBLISHING.md) · [Changelog](CHANGELOG.md) |

Try the offline demo from a source checkout; it needs no account and calls no live services:

```sh
python3 plugins/plane-for-codex/scripts/plane_workflow.py demo
```

Runtime Python helpers use only the standard library. Development checks and decision evals are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

---

Community-maintained by [SoaringLabs](https://github.com/SoaringLabs). Not affiliated with Plane or OpenAI. [MIT License](LICENSE).
