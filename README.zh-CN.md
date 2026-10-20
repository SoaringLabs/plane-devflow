<p align="center">
  <img src="plugins/plane-for-codex/assets/icon.png" alt="Plane for Codex 标志" width="88" height="88">
</p>
<h1 align="center">Plane for Codex</h1>
<p align="center">
  <a href="https://github.com/SoaringLabs/plane-for-codex/releases"><img src="https://img.shields.io/github/v/release/SoaringLabs/plane-for-codex?color=7661d8" alt="最新版本"></a>
  <a href="https://github.com/SoaringLabs/plane-for-codex/stargazers"><img src="https://img.shields.io/github/stars/SoaringLabs/plane-for-codex?style=flat&amp;color=7661d8" alt="GitHub Stars"></a>
  <a href="https://github.com/SoaringLabs/plane-for-codex/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/SoaringLabs/plane-for-codex/validate.yml?branch=main&amp;label=checks" alt="主分支检查状态"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT 许可"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10 及以上"></a>
</p>
<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>
<p align="center"><strong>从 Plane 任务，到可审阅的 Pull Request。</strong><br>独立开发，衔接上下文，交付清晰可查。</p>
<p align="center"><a href="#快速开始">快速开始</a> · <a href="#功能">功能</a> · <a href="#技能入口">技能入口</a> · <a href="#文档">文档</a> · <a href="CHANGELOG.md">更新记录</a></p>
<p align="center"><img src="docs/assets/workflow.svg" alt="流程示意：Plane 任务 → Codex 独立任务工作区 → 关联的 GitHub PR。DEMO-123 为示例任务。" width="100%"></p>

将 **Plane 任务、Codex 开发和 GitHub PR** 串成一条工作流的社区开源插件。从任务需求出发，在独立目录中开发，再交付附有验证与验收记录的关联 PR。无需部署额外服务。

## 快速开始

### 安装

复制这条命令到终端执行：

```sh
codex plugin marketplace add SoaringLabs/plane-for-codex && \
  codex plugin add plane-for-codex@plane-for-codex
```

Codex 会获取仓库并安装完整插件，无需手动克隆、填写本地路径或安装 npm 引导程序。需要支持插件的 Codex CLI、Git 和 Python 3.10+；PR 操作还需要已登录的 [GitHub CLI](https://cli.github.com/)。

在**目标代码仓库新开一个 Codex 聊天**，选择 **Plane: 初始化**，按引导选择项目，并在需要时通过浏览器授权 Plane。账号授权与 GitHub 后台同步配置是两个步骤。已有本地 marketplace 安装的用户，请先看 [迁移说明](docs/installation.md#existing-local-marketplace-installations)。

### 开始第一条任务

下面的 `PROJECT-123` 是示例，请替换为项目中已有任务的真实编号。

| 步骤 | 在 Codex 中操作 | 应看到的结果 |
| --- | --- | --- |
| 关联 | 选择 **Plane: 初始化** | 已关联的项目，以及同步验证结果或具体待完成步骤 |
| 开发 | `$plane-for-codex:plane-start 开始 PROJECT-123` | 任务专属目录、分支、需求与验收范围 |
| 交付 | `$plane-for-codex:plane-deliver 交付 PROJECT-123，先不要合并` | 关联 PR、实际检查结果和待验收项 |

初始化生成的 `.plane-for-codex.json` 需要先进入配置的基础分支，才能创建独立任务分支。仅核对需求时，可以明确要求“只讨论，不保存文件”。交付、验收与合并各按请求范围执行，已有授权会复用。

## 功能

| 能力 | 带来的帮助 |
| --- | --- |
| **任务独立工作区** | 每个任务使用独立目录与分支，保留主目录和其他任务的改动 |
| **恢复正确版本** | 再次开始或换聊天时，恢复该任务记录的目录与上下文 |
| **关联 PR 交付** | 一条任务对应一个主 PR，在 Plane 中保留实现与验证报告 |
| **按需准备试用** | 需要时运行任务版本，提供可用入口与测试步骤 |
| **GitHub 后台同步** | 通过 Actions 或已配置的 Plane 官方集成记录 PR 事件 |
| **清晰的验收与完成** | 区分运行就绪、人工验收与合并授权 |

交付后可说：“帮我运行 PROJECT-123 的任务工作区代码，我来验收。”Codex 会依据项目自身的运行/构建说明准备入口，核对实际来源版本，再交接测试。只交付 PR 不会强制启动环境。详见 [验收环境交接](plugins/plane-for-codex/references/acceptance-environment.md)。

## 技能入口

在 Codex 的技能选择菜单中搜索 **Plane**。当前菜单标签为中文，完整技能标识在两种语言下均可使用。

| 入口 | 什么时候用 |
| --- | --- |
| **Plane: 初始化** | 关联项目，检查或调整映射，继续同步配置 — `$plane-for-codex:plane-setup` |
| **Plane: 开始任务** | 讨论、规划、开始或恢复已有任务 — `$plane-for-codex:plane-start` |
| **Plane: 交付任务** | 交付 PR、准备试用、记录验收或按授权收尾 — `$plane-for-codex:plane-deliver` |

这些是 Skill 入口，没有独立的 `/plane` 命令或配置页面。请安装完整插件；当前不支持单独复制各个技能目录使用。

## GitHub 同步

| 方式 | 需要准备 |
| --- | --- |
| **GitHub Actions（默认）** | 单独的 Plane PAT，存入仓库 Secret `PLANE_API_KEY`；同步文件需要合入默认分支 |
| **Plane 官方 GitHub 集成** | 已启用并核对仓库、项目映射及规则；无需本插件的 workflow 或 PAT Secret |

关联项目使用浏览器授权，不需要 PAT。Actions 的 PAT 请直接在 GitHub Secrets 或由本人操作的隐藏终端输入中录入，不要发送到聊天。

初始化中断或条件不足时会保存进度，之后可继续。**连接验证通过与真实 PR 事件回写成功会分别报告。** 新基础映射记录 PR 活动，保留任务状态；旧映射沿用既有规则，原生集成的状态变化由官方集成控制。详见 [初始化与同步](plugins/plane-for-codex/references/setup.md)。

## 使用范围

当前支持已有任务、一条任务对应一个主 PR、Plane Cloud 和 github.com。Cycle/任务管理、自定义状态规则、多 PR 聚合、完整的自托管 Plane 与 GitHub Enterprise 接入暂不支持。

## 更新与移除

刷新 Git 来源的 marketplace，再更新插件：

```sh
codex plugin marketplace upgrade plane-for-codex && codex plugin add plane-for-codex@plane-for-codex
```

随后新开聊天加载。移除插件使用 `codex plugin remove plane-for-codex@plane-for-codex`。插件更新或移除不会升级或删除业务仓库中的映射、已复制的 workflow/脚本、任务工作区或外部账号配置。切换已有本地安装来源前，请看 [安装与迁移说明](docs/installation.md)。

## 文档

| 想了解什么 | 文档 |
| --- | --- |
| 安装、更新与迁移 | [安装、更新、迁移及移除](docs/installation.md) |
| 初始化与恢复 | [项目关联与同步](plugins/plane-for-codex/references/setup.md) · [中断后继续](plugins/plane-for-codex/references/recovery.md) |
| 开发与交接 | [任务执行](plugins/plane-for-codex/references/task-execution.md) · [并行任务](plugins/plane-for-codex/references/parallel-tasks.md) · [验收环境](plugins/plane-for-codex/references/acceptance-environment.md) |
| 配置格式 | [基础映射](examples/plane-for-codex.basic.json) · [旧映射](examples/plane-for-codex.example.json) |
| 贡献与发布 | [贡献指南](CONTRIBUTING.md) · [架构](docs/architecture.md) · [发布指南](PUBLISHING.md) · [更新记录](CHANGELOG.md) |

在源码目录运行离线演示，无需账号，也不会调用真实服务：

```sh
python3 plugins/plane-for-codex/scripts/plane_workflow.py demo
```

插件运行时的 Python helper 仅使用标准库。开发检查与决策评测见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

由 [SoaringLabs](https://github.com/SoaringLabs) 社区维护，与 Plane / OpenAI 无官方隶属关系。采用 [MIT License](LICENSE)。
