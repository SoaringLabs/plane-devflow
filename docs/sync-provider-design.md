# Plane 与 GitHub 同步模式

2026-10-10。0.4.0 已实现原生／Actions 模式和 v1 默认、v2 按需路由；其余后续设计在下文标明。依据见 [官方资料核对](plane-github-capability-research.md) 与 [真实验证](plane-github-capability-verification.md)。映射格式 1／2 与 API 版本彼此独立；无 sync 字段的旧配置默认 Actions＋v1。

## 产品决定

当前提供 `native`、`actions` 两种后台同步选择；`none` 独立协议值留待后续，暂缓配置仍报告部分完成。选择依据是实际配置和用户意愿，不仅是套餐名称。

| 模式 | 适用情况 | 初始化完成条件 |
| --- | --- | --- |
| native | 有对应套餐且已启用官方 GitHub 集成 | 确认组织授权、目标仓库与 Plane 项目映射、原生状态规则；不要求安装本插件 Actions 或配置 PAT Secret |
| actions | Free 用户，或希望使用插件自定义同步规则的付费用户 | 默认分支有可信 workflow／脚本／关联配置；PAT Secret 就绪；真实 runner 连接检查通过；事件写回另行报告 |
| none | 用户明确暂不启用后台同步 | 保存关联，说明 GitHub 事件不会由插件自动写回；之后可继续配置 |

付费用户仍可以选择 Actions；拥有 Pro 不代表 GitHub 已经连接。官方 GitHub 集成目前列入 Pro／Business／Enterprise。[Plane Marketplace](https://plane.so/marketplace/github)

原生模式仍保留 Codex 的需求整理、项目／Cycle／任务管理、准备分支和交付报告能力。同一个 PR 生命周期事件只能由一个同步方写状态；使用原生模式时，插件的 Start／Deliver 也必须遵守动作归属，不再重复自动写与原生重叠的状态。

## 三层分别检查

1. 账号：Plane MCP OAuth 与 GitHub CLI 用于用户当前会话的操作。
2. 关联：仓库对应哪个工作区、项目和具体任务。
3. 后台执行：由官方服务或 Actions 消费 GitHub 事件。

截图中的个人 GitHub 连接提示主要证明授权／关联步骤完成，不能单独证明所有仓库映射和状态规则都已配置。Linear 官方流程也区分安装组织／仓库 GitHub App 和认证个人账号。[Linear GitHub integration](https://linear.app/docs/github)

因此，不能把“OAuth 已连接”“PAT Secret 存在”“workflow 绿色”“状态回写成功”合并成一个 connected 标记。初始化状态需分别报告：关联已保存、后台执行器就绪、连接验证通过、事件写回已验证。失败的新运行覆盖旧的成功结果。

## 事件与规则

后续自定义规则设计（尚未实现）：Actions 只执行明确配置的动作。每个动作选择实际状态 UUID 或保持当前状态，并可限定来源状态；不会创建或猜测 In Review，也不要求三个状态互不相同。原生模式读取并展示其规则，不假装插件控制官方服务内部行为。

- PR 草稿／就绪／关闭／重开／合并只记录各自事实。
- 人工验收和 PR 合并独立；需要验收时，合并不能代替验收。
- 自动事件保护 completed／cancelled 以及用户主动设置的状态；读最新 PR 与 Plane 状态，处理迟到事件和重试。
- Issue 关闭到完成只是本次隔离验证使用的显式规则，不作为所有项目的默认验收策略。
- 评论以来源对象 key upsert；链接先查询规范化 URL，避免重复创建。
- 集合更新先读、计算期望集合、写入、回读；不把 HTTP 200 当成期望状态已实现。

upsert 的顺序重放已验证，但跨仓库并发尚未验证。单仓库 concurrency 无法覆盖两个仓库同时更新一个任务，扩展时需要共享协调或限制归属。

## 免费路径的边界

工程判断：对于当前少量仓库、GitHub → Plane、无需常驻服务的要求，Actions 是可维护的选择。官方服务能减少用户配置与维护，但没有适用于所有团队的“行业最优解”。长期多仓库、多用户、双向实时同步可以演进为自建 GitHub App＋webhook 服务；这会增加服务运维和授权生命周期管理。

纯 Actions 不是 Plane webhook 接收端。Plane → GitHub 实时同步需要可达接收服务或定时轮询，还要定义字段归属、去重和防回环。此阶段不宣称与官方集成完全等价。

私有仓库标准 Ubuntu runner 使用仓库所属账号的共享免费额度；额度可能与已有 CI 共用。避免不必要的 artifacts／cache，报告套餐和预算限制。[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

## 实施顺序与验收

1. 已实现：在现有格式中可选保存 sync.provider / sync.api_version；无此字段的旧配置默认 Actions＋v1，保留状态和完成规则。
2. 修改 Setup、readiness 检查、生成器与交付规则：native 不要求 Actions；actions 保留真实 runner 验证；none 独立协议值暂未实现，用户暂缓时保持部分完成。
3. provider 切换先禁用旧写入方，再启用新方；旧 PR 绑定和未完成任务保留原归属，不能随项目重配被重定向。
4. 优先交付 PR 关联、生命周期记录与显式状态规则；Issue／评论同步为可选扩展，不能默认复制全部仓库内容。
5. Cycle／Module 与项目任务管理复用官方 MCP；附件以实际 byte 回读确认，PAT runner 的附件链路另行验收。
6. 使用本次隔离验证发现的边界做兼容检查；标签／负责人清除、fork／Dependabot、双向 webhook、多仓库并发都有独立验收项。

新字段和版本号需与现有校验器、bundled runner、旧 pinned Action 一起设计。`native` / `actions` 已是可提交的 sync.provider 值；`none` 尚不是。

当前实现：原生凭据记录真实 UI 观察或用户确认，绑定配置摘要；不能自动发现官方集成。Actions 文件升级需审阅摘要并备份。明确选择 v2 时仍用 v1 读取安全决策所需状态／标签，避免已观察到的关系延迟。Issue／评论事件等扩展没有默认启用。
