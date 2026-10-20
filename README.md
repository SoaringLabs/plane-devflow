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
<p align="center"><img src="docs/assets/workflow.svg" alt="Workflow illustration: Plane task → isolated Codex workspace → linked GitHub pull request. DEMO-123 is an example." width="100%"></p>

An open-source community plugin that connects **Plane tasks, Codex development and GitHub PRs**. Start with the task's requirements, work in its own directory, and deliver a linked PR with verification and acceptance records. No additional service to deploy.

## Quick start

### Install

Run this command in your terminal:

```sh
codex plugin marketplace add SoaringLabs/plane-for-codex && \
  codex plugin add plane-for-codex@plane-for-codex
```

Codex fetches the repository and installs the complete plugin. No manual clone, local path or npm bootstrap is needed. Requires a plugin-enabled Codex CLI, Git and Python 3.10+; PR operations also need an authenticated [GitHub CLI](https://cli.github.com/).

Open a **new Codex chat in your target repository**, select **Plane: 初始化**, and follow setup to choose a project and authorize Plane in your browser when needed. Account authorization and GitHub background-sync configuration are separate steps. Existing local-marketplace installs should follow the [migration guide](docs/installation.md#existing-local-marketplace-installations).

### Start your first task

`PROJECT-123` below is an example; replace it with an existing task ID.

| Step | In Codex | Expected result |
| --- | --- | --- |
| Connect | Select **Plane: 初始化** | Project association and verified sync, or the precise remaining setup step |
| Develop | `$plane-for-codex:plane-start Start PROJECT-123` | The task's own working directory, branch, requirements and acceptance scope |
| Deliver | `$plane-for-codex:plane-deliver Deliver PROJECT-123; keep the PR open` | A linked PR, actual check results and outstanding acceptance items |

Setup's `.plane-for-codex.json` must reach the configured base branch before independent task branches are created. You can also ask to read a task and discuss it without saving files. Delivery, acceptance and merge follow the requested scope; existing authorization is reused.

## Features

| Capability | What it gives you |
| --- | --- |
| **Independent task workspaces** | A separate directory and branch for each task, preserving the primary checkout and other tasks' edits |
| **Resume the right version** | Recover the task's recorded directory and context when continuing in another chat |
| **Linked PR delivery** | Keep one primary PR tied to the task, with implementation and verification reports in Plane |
| **Test when you're ready** | Ask Codex to prepare the task version for manual testing, with a usable entry point and test steps |
| **Background GitHub sync** | Record PR events through GitHub Actions or an existing official Plane integration |
| **Clear acceptance and completion** | Keep runtime readiness, human acceptance and merge authorization separate |

To try a delivered result, say: “Run PROJECT-123 from its task workspace so I can test it.” Codex follows the project's own run/build instructions, checks the source version and hands over the entry point. PR delivery alone does not start an environment. See [acceptance handoff](plugins/plane-for-codex/references/acceptance-environment.md).

## Skills

Search **Plane** in Codex's skill picker. Display labels currently appear in Chinese; full identifiers work in either language.

| Skill | Use when |
| --- | --- |
| **Setup** · `Plane: 初始化` | Associate a project, inspect/reconfigure the mapping, or resume sync setup — `$plane-for-codex:plane-setup` |
| **Start** · `Plane: 开始任务` | Discuss, plan, start or resume an existing task — `$plane-for-codex:plane-start` |
| **Deliver** · `Plane: 交付任务` | Deliver a PR, prepare testing, record acceptance or finalize authorized work — `$plane-for-codex:plane-deliver` |

These are skills, not a separate `/plane` command or settings page. Install the complete plugin; standalone copies of individual skill folders are not a supported installation.

## GitHub synchronization

| Provider | Requirements |
| --- | --- |
| **GitHub Actions** — default | A separate Plane PAT in the repository Secret `PLANE_API_KEY`, plus sync files merged into the default branch |
| **Official Plane integration** | An enabled and verified repository/project mapping and rules; no plugin workflow or PAT Secret |

Project association uses browser authorization, without a PAT. For Actions, enter the PAT directly through GitHub Secrets or a human-operated hidden terminal prompt. Keep it out of chat.

Incomplete setup is saved and resumable. **A successful connection check and a real PR-event writeback are reported separately.** New basic mappings record PR activity without changing task states; legacy mappings retain their existing rules. Native transitions belong to the official integration. See [setup and sync](plugins/plane-for-codex/references/setup.md).

## Scope

Currently supports existing tasks, one primary PR per task, Plane Cloud and github.com. Cycle/task management, custom status rules, multi-PR aggregation, full self-hosted Plane and GitHub Enterprise support are outside the current scope.

## Update or remove

Refresh the Git-backed marketplace and reinstall the plugin:

```sh
codex plugin marketplace upgrade plane-for-codex && codex plugin add plane-for-codex@plane-for-codex
```

Then open a new chat. For removal, run `codex plugin remove plane-for-codex@plane-for-codex`. Plugin updates/removal do not update or delete business-repository mappings, copied workflows/scripts, task workspaces or external account configuration. See [installation and migration](docs/installation.md) before changing an existing local source.

## Documentation

| Topic | Read more |
| --- | --- |
| Installation and updates | [Install, update, migrate and remove](docs/installation.md) |
| Setup and recovery | [Project association & sync](plugins/plane-for-codex/references/setup.md) · [Resume setup](plugins/plane-for-codex/references/recovery.md) |
| Development and handoff | [Task execution](plugins/plane-for-codex/references/task-execution.md) · [Parallel tasks](plugins/plane-for-codex/references/parallel-tasks.md) · [Acceptance environments](plugins/plane-for-codex/references/acceptance-environment.md) |
| Configuration | [Basic mapping](examples/plane-for-codex.basic.json) · [Legacy mapping](examples/plane-for-codex.example.json) |
| Contributing and releases | [Contributing](CONTRIBUTING.md) · [Architecture](docs/architecture.md) · [Publishing](PUBLISHING.md) · [Changelog](CHANGELOG.md) |

Try the offline demo from a source checkout; it needs no account and calls no live services:

```sh
python3 plugins/plane-for-codex/scripts/plane_workflow.py demo
```

Runtime Python helpers use only the standard library. Development checks and decision evals are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

---

Community-maintained by [SoaringLabs](https://github.com/SoaringLabs). Not affiliated with Plane or OpenAI. [MIT License](LICENSE).
