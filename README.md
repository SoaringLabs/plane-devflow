# Plane for Codex

把 Plane 任务、Codex 开发和 GitHub PR 串成一条工作流的社区开源插件。

**关联项目 → 开始任务 → 开发与验证 → 交付 PR → 验收与收尾**

- 在 Codex 中选择或创建 Plane 项目，关联当前代码仓库。
- 为不同任务准备独立工作目录和分支，让多个聊天可以同时开发。
- 创建或更新关联任务的 PR，将交付记录回写 Plane。
- 通过 GitHub Actions 或已配置的 Plane 官方 GitHub 集成同步 PR 进展。

无需部署额外服务。Python 脚本只使用标准库。

## 安装

需要支持插件的 Codex、Git、Python 3.10+；PR 操作还需要已登录的 [GitHub CLI](https://cli.github.com/)（`gh auth login`）。

```sh
git clone https://github.com/SoaringLabs/plane-for-codex.git
cd plane-for-codex
codex plugin marketplace add /absolute/path/to/plane-for-codex --json
codex plugin add plane-for-codex@plane-for-codex --json
codex mcp login plane
```

将 `/absolute/path/to/plane-for-codex` 替换为克隆目录的**绝对路径**，随后在浏览器完成 Plane 授权。已有同名 `plane` MCP 连接时，先检查是否冲突。

安装或更新后，在目标代码仓库新开一个 Codex 聊天加载插件。更新时重新执行上面的 `codex plugin add` 命令即可。

## 开始使用

在 Codex 的技能选择菜单中搜索 **Plane**，选择对应入口并发送。菜单打开方式随客户端而异；支持 `/` 技能菜单的版本可输入 `/` 搜索。

| 入口 | 什么时候用 | 会做什么 |
| --- | --- | --- |
| **Plane: 初始化** | 首次使用，或检查、调整已有配置 | 引导选择项目、关联仓库并配置 GitHub 同步 |
| **Plane: 开始任务** | 准备处理一个已有任务 | 读取需求，准备独立目录与分支；再次开始时恢复原任务 |
| **Plane: 交付任务** | 改动准备好后 | 检查验证与验收情况，创建或更新 PR，回写交付记录 |

初始化直接选择并发送即可；开始任务时可附上任务编号或链接。初始化生成的 `.plane-for-codex.json` 需要进入仓库的目标基础分支，之后才能创建独立任务分支。

也可使用完整技能标识：`$plane-for-codex:plane-setup`、`$plane-for-codex:plane-start`、`$plane-for-codex:plane-deliver`。这些是 Skill 入口，没有单独的 `/plane` 命令或配置页面。

开发前会整理需求和验收标准，交付时检查当前改动的验证记录。任务合并并确认完成后，会尝试更新主工作目录；遇到未提交改动等阻碍时保留现场。详细规则见 [任务执行与验收](plugins/plane-for-codex/references/task-execution.md)。

## GitHub 同步

初始化会引导配置并验证一种后台同步方式，让 Codex 关闭后发生的 PR 事件也能回写 Plane。

| 方式 | 需要准备 |
| --- | --- |
| **GitHub Actions（默认）** | Plane PAT、仓库 Secret `PLANE_API_KEY`，以及合入默认分支的同步文件 |
| **Plane 官方 GitHub 集成** | 已启用并核对仓库、项目映射及规则的官方集成，无需本插件的 workflow 或 PAT Secret |

关联项目使用 Plane 浏览器授权，不需要 PAT；Actions 使用单独的凭证。PAT 请通过隐藏终端输入或 GitHub Secrets 页面录入，勿发送到聊天。

缺少凭证、权限或验证时，初始化会保留进度并报告部分完成，之后可继续配置。**连接验证通过与真实 PR 事件回写成功会分别报告。** 配置细节见 [初始化与同步](plugins/plane-for-codex/references/setup.md)。

## 使用范围

- 当前支持已有任务的开发与交付，一条任务对应一个主 PR。
- 新基础配置只同步 PR 记录，保留任务状态；旧配置沿用原有状态与人工验收规则。官方集成的状态变化由其自身规则控制。
- Cycle、任务创建与管理、自定义状态规则、多 PR 聚合和上下文自动推进尚未实现。
- 当前面向 Plane Cloud 与 github.com；完整的自托管 Plane 和 GitHub Enterprise 接入尚未支持。

## 文档与演示

| 想了解什么 | 文档 |
| --- | --- |
| 初始化、重新配置与同步 | [配置指南](plugins/plane-for-codex/references/setup.md) · [中断后继续配置](plugins/plane-for-codex/references/recovery.md) |
| 需求、验证、验收与交付 | [任务执行与验收](plugins/plane-for-codex/references/task-execution.md) |
| 多聊天开发与合并冲突 | [并行任务](plugins/plane-for-codex/references/parallel-tasks.md) |
| 分支检查与完成后收尾 | [工作目录管理](plugins/plane-for-codex/references/checkout.md) |
| 配置文件格式 | [基础配置示例](examples/plane-for-codex.basic.json) · [旧配置示例](examples/plane-for-codex.example.json) |
| 版本、架构与贡献发布 | [更新记录](CHANGELOG.md) · [架构](docs/architecture.md) · [发布指南](PUBLISHING.md) |

无需账号即可运行本地演示；演示不会操作真实 Plane 或 GitHub：

```sh
python3 plugins/plane-for-codex/scripts/plane_workflow.py demo
```

开发验证：`python3 -m unittest discover -s tests -v`。

## English

Plane for Codex connects Plane tasks, isolated development workspaces and GitHub PRs. Install with the commands above, then select **Plane: 初始化** (Setup), **Plane: 开始任务** (Start task), or **Plane: 交付任务** (Deliver task) in Codex. GitHub background sync uses Actions or an existing official Plane integration. New basic mappings preserve task states; legacy mappings retain their existing rules. See the [setup guide](plugins/plane-for-codex/references/setup.md) for details.

---

社区维护，与 Plane / OpenAI 无官方隶属关系。采用 [MIT License](LICENSE)。
