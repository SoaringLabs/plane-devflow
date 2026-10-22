<p align="center">
  <img src="plugins/plane-devflow/assets/icon.png" alt="Plane DevFlow logo" width="88" height="88">
</p>
<h1 align="center">Plane DevFlow</h1>
<p align="center">
  <a href="https://github.com/SoaringLabs/plane-devflow/releases"><img src="https://img.shields.io/github/v/release/SoaringLabs/plane-devflow?color=7661d8" alt="Latest release"></a>
  <a href="https://github.com/SoaringLabs/plane-devflow/stargazers"><img src="https://img.shields.io/github/stars/SoaringLabs/plane-devflow?style=flat&amp;color=7661d8" alt="GitHub stars"></a>
  <a href="https://github.com/SoaringLabs/plane-devflow/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/SoaringLabs/plane-devflow/validate.yml?branch=main&amp;label=checks" alt="Main branch checks"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10 or newer"></a>
</p>
<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>
<p align="center"><strong>Connect Plane, your coding agent, and GitHub.</strong><br>Develop tasks. Deliver PRs. Sync PR activity—without Plane’s paid GitHub integration.</p>
<p align="center"><a href="#features">Features</a> · <a href="#quick-start">Quick start</a> · <a href="#skills">Skills</a> · <a href="#documentation">Docs</a> · <a href="CHANGELOG.md">Changelog</a></p>
<p align="center"><img src="docs/assets/workflow.svg" alt="Example workflow: Plane task DEMO-123 → coding agent in an isolated workspace → linked GitHub PR. GitHub Actions records PR activity back in Plane." width="100%"></p>

Open-source Agent Skills with integration guides for **Codex, Claude Code, Cursor and OpenCode**. Work from a Plane task, deliver a linked PR, and use GitHub Actions to record PR activity back in Plane. No extra service to deploy.

## Features

| What you can do | What you get |
| --- | --- |
| **Connect Plane and GitHub** | Link a task to its primary PR and record PR activity through GitHub Actions, without Plane’s paid GitHub integration |
| **Develop from a task** | Give your agent a task ID; it reads the requirements and prepares a dedicated directory and branch |
| **Track delivery in Plane** | Find the linked PR, implementation summary, actual check results and outstanding acceptance items in the task |
| **Keep tasks separate** | Work in isolated workspaces and resume the recorded task version in another chat |
| **Start a new project** | Follow setup from repository preparation to Plane association, then review a first task list before creation |
| **Diagnose a task** | See checkout, verification, PR/CI, writeback and remaining handoff separately through a read-only summary |
| **Try the result before merging** | Ask your agent to run the task version and provide an entry point and test steps; acceptance and merge remain separate decisions |

New setups record PR activity **without automatically changing task states**. See [GitHub synchronization](#github-synchronization) for setup and existing integration options.

## Quick start

### Install

The stable-channel command below requires a published product release and an activated `stable` branch. Until both are available, use the candidate-testing instructions in the [installation guide](docs/installation.md).

Run from your target repository’s root and choose your agent:

```sh
npx skills add https://github.com/SoaringLabs/plane-devflow/tree/stable \
  --skill plane-setup plane-start plane-deliver
```

The command installs all three skills in the current project. Add `--global` to make them available across projects. See the [installation guide](docs/installation.md) for prerequisites, host selection, MCP configuration and the Codex plugin distribution.

### Connect → develop → deliver

Open a **new agent session in the target repository**. Replace `PROJECT-123` with your task ID.

| Step | Ask your agent | Expected result |
| --- | --- | --- |
| Connect | “Use plane-setup to connect this repository to Plane and configure GitHub sync” | Project association and verified sync, or the specific remaining setup step |
| Develop | “Use plane-start to start PROJECT-123” | The task’s own directory and branch, with requirements and acceptance scope |
| Deliver | “Use plane-deliver to deliver PROJECT-123; keep the PR open” | A linked PR, verification report and outstanding acceptance items |

To test the result, say: **“Run PROJECT-123 from its task workspace so I can test it.”** The agent follows the project’s run/build instructions and checks the source version before handing over the entry point. See [acceptance handoff](skills/plane-deliver/references/acceptance-environment.md).

**No repository or tasks yet?** Start with the [first-project guide](docs/first-project.md). For an existing project, say: “Use plane-start to draft the first version; show me the task list before creating anything.” Review the exact list before asking to create tasks. See [task planning](skills/plane-start/references/task-planning.md).

Each repository runs setup once and keeps its mapping in `.plane-devflow.json`. That mapping must reach the configured base branch before independent task branches are created. Installing skills does not complete account authorization or activate GitHub sync; setup verifies each step and reuses existing connections.

## Skills

Use your host’s skill picker or request a skill by name. Invocation, MCP setup and tested limits are covered in the [agent compatibility guide](docs/agent-compatibility.md).

| Skill | Use when |
| --- | --- |
| **Set Up Plane** — `plane-setup` | Connect a repository, configure GitHub sync or resume incomplete setup |
| **Start Plane Task** — `plane-start` | Plan the first tasks, create an approved list, or start/resume an existing task |
| **Deliver Plane Task** — `plane-deliver` | Deliver or diagnose a task PR, prepare testing, record acceptance or finalize authorized work |

Codex standalone skills use `$plane-setup`; the Codex plugin uses `$plane-devflow:plane-setup`. Claude Code uses `/plane-setup`; OpenCode loads the named skill through its native tool. Choose one distribution to avoid duplicate entries. Each skill is self-contained and can also be installed individually.

## GitHub synchronization

**GitHub Actions is the default:** linked PR events are recorded in Plane independently of the agent session. It does not require Plane’s paid GitHub integration or an extra service to deploy.

| Provider | Requirements |
| --- | --- |
| **GitHub Actions** — default | A Plane PAT in the repository Secret `PLANE_API_KEY`, plus the mapping and sync files merged into the default branch |
| **Official Plane integration** — optional | An enabled and verified repository/project mapping and rules; no plugin workflow or PAT Secret |

Project association uses browser authorization. Actions uses a separate PAT: enter it directly through GitHub Secrets or a human-operated hidden terminal prompt, never in chat. Optional [local credential reuse](skills/plane-setup/references/local-credentials.md) uses macOS Keychain or Windows Credential Manager. On macOS, an explicitly authorized [create-and-save flow](skills/plane-setup/references/local-credentials.md#automatic-creation-from-plane-app) can reuse a valid Plane App session without copying a PAT; expired sessions prompt login.

Incomplete setup is saved and resumable. **Connection verification, an observed PR-event run and confirmed task writeback are separate evidence.** Routine remote metadata checks run at most once per 24 hours, including failed attempts; expired evidence is reported without automatic connection-test dispatch. Task diagnosis defaults to local records/cache; an explicit refresh reads current remote facts. New mappings record PR activity without state transitions; legacy mappings retain existing rules, and native transitions belong to the official integration. See [setup and sync](skills/plane-setup/references/setup.md).

## Scope

Supports first-version task drafting and approved creation, existing-task development, one primary PR per task, Plane Cloud and github.com. General task/Cycle/Module management, custom status rules, multi-PR aggregation, full self-hosted Plane and GitHub Enterprise support are outside the current scope.

Local task records support recovery in another chat when the host provides trusted context. Cross-machine conversation/session portability belongs to the host agent. See the [capability and evidence matrix](docs/capabilities.md) for implementation, test depth and remaining limits.

## Update or remove

### Update

Ask your agent: **“Use plane-setup to upgrade Plane DevFlow in this repository; show the target release, changelog and plan first.”** One product version covers the skills and public GitHub Action. The flow preserves your installation channel and coordinates the local refresh, project upgrade PR, activation and verification.

To refresh only the skill files, rerun the installation command:

```sh
npx skills add https://github.com/SoaringLabs/plane-devflow/tree/stable --skill '*'
```

Add `--global` for your original global installation and open a new agent session afterward. File refresh alone does not upgrade the project's Action reference. For selected-skill updates, plugin handoffs, recovery and rollback, see the [installation guide](docs/installation.md#update-or-remove-standalone-skills).

### Remove

Run from the same repository and select the intended agent:

```sh
npx skills remove plane-setup plane-start plane-deliver
```

For a global installation, add `--global`. Removal preserves MCP connections, account authorization, project mappings, copied sync files and task workspaces. For Codex plugin removal, see the [installation guide](docs/installation.md#install-the-codex-plugin-locally).

## Documentation

| Topic | Read more |
| --- | --- |
| First project | [New-computer preparation, handoffs and first tasks](docs/first-project.md) |
| Agent compatibility | [Codex, Claude Code, Cursor and OpenCode](docs/agent-compatibility.md) |
| Installation and updates | [Install, update, migrate and remove](docs/installation.md) |
| Setup and recovery | [Project association & sync](skills/plane-setup/references/setup.md) · [Resume setup](skills/plane-setup/references/recovery.md) |
| Task diagnosis | [Read-only task status and partial progress](skills/plane-deliver/references/task-diagnostics.md) |
| Capabilities and evidence | [Current inventory and verification boundaries](docs/capabilities.md) |
| Development and handoff | [Task execution](skills/plane-start/references/task-execution.md) · [Parallel tasks](skills/plane-start/references/parallel-tasks.md) · [Acceptance environments](skills/plane-deliver/references/acceptance-environment.md) |
| Configuration | [Basic mapping](examples/plane-devflow.basic.json) · [Legacy mapping](examples/plane-devflow.example.json) |
| Contributing and releases | [Contributing](CONTRIBUTING.md) · [Architecture](docs/architecture.md) · [Publishing](PUBLISHING.md) · [Changelog](CHANGELOG.md) |

Try the offline demo from a source checkout; it needs no account and calls no live services:

```sh
python3 plugins/plane-devflow/scripts/plane_workflow.py demo
```

Runtime Python helpers use only the standard library. Development checks and decision evals are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

---

Community-maintained by [SoaringLabs](https://github.com/SoaringLabs). Not affiliated with Plane or OpenAI. [MIT License](LICENSE).
