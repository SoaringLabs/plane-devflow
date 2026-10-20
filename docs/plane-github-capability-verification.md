# Plane Free 与 GitHub Actions：真实能力验证

日期：2026-10-10，Plane Cloud，隔离的测试工作区。经用户授权执行真实写入和扩展验证；临时 PAT Secret 由用户直接在 GitHub 保存，未启用付费套餐。Plane 应用工作区设置显示 **Free / Owner**，不是从 feature flags 推断套餐。

本公开记录已移除真实工作区、项目和对象标识、私有仓库地址及 Actions 运行编号。原始运行证据保留在未发布的验证资料中；下文是历史验证摘要，读者无法通过本文独立查验私有日志。扩展探测能力不等于发布插件已实现对应功能。

## 结论

该次验证中的免费工作区允许 Actions 使用 PAT REST API 完成 PR 状态／记录回写，以及任务、评论、链接、标签、负责人、父子任务、Cycle／Module 等基础操作。真实 GitHub Issue 与评论事件也可以转写 Plane，不必购买官方 GitHub 集成。

这证明免费 API 路径可行，不代表实现了官方集成的全部能力，更不代表全部 Plane 免费账号／自托管版本都与此环境相同。2026-10-10 核对的官方资料将该集成列入 Pro、Business、Enterprise。[Plane Marketplace](https://plane.so/marketplace/github)

## 隔离范围

- 临时 Plane 项目：仅含合成数据，项目标识和 UUID 已移除。
- GitHub 私有测试仓库：地址已移除；测试 PR 与 Issue 只包含合成内容。
- PR 路径使用验证当时源码的 bundled `action_runner.py`／`plane_sync.py`；扩展能力与 Issue 转写使用独立验证脚本，尚未加入发布插件。
- 不修改业务项目、业务任务、业务仓库配置或仓库 Secret。本地现有未提交的插件改造保持原样。
- PAT 只由 runner 从 Secret 读取；脚本不输出请求 headers、凭据、任意响应正文。固定 Cloud host，拒绝 HTTP 重定向，先核对测试项目 identifier／external source，再执行写入。
- workflow 只执行可信默认分支脚本；固定 checkout SHA、只读 GITHUB_TOKEN，不执行 PR head 代码。

## 能力矩阵

“MCP”是现有 OAuth 连接；“Actions REST”是真实 Ubuntu runner 中的 PAT。两个认证层分别验证。

| 能力 | MCP OAuth | Actions REST | 证据／限制 |
| --- | --- | --- | --- |
| 项目创建、更新；自定义状态创建、改名 | 通过 | 项目／状态读取通过，未测创建 | 所有写入只在隔离项目 |
| 任务 CRUD、标题、HTML 描述、优先级、日期、状态 | 通过 | 通过 | 写入后读实际记录；UUID 与人类标识符查找、分页也通过 |
| 标签创建／更新／绑定；负责人绑定／清除 | 通过 | 写入通过，v2 ID 数组回读不一致 | v1 与 MCP 交叉读取确认空集合；见下方异常说明 |
| 父子任务建立／解除 | 通过 | 通过 | `parent`／`parent_id` 不同版本分别处理 |
| 评论 CRUD、同 key upsert | 通过 | 通过 | 顺序重放保留同一 UUID／一条记录，未测并发竞争 |
| 外链 CRUD | 通过 | 通过 | 私有仓库 URL 的匿名 metadata 抓取可返回 404，不代表链接创建失败 |
| Cycle CRUD、任务加入／移除 | 创建／修改／加入／读取通过 | 通过 | POST membership；GET 项目任务按 cycle_id 过滤 |
| Module CRUD、任务加入／移除 | 创建／修改／加入／读取通过 | 通过 | POST membership；GET 项目任务按 module_id 过滤 |
| 审计活动读取 | 通过 | 通过 | 只读；不承诺写入 activity |
| 任务归档／恢复 | 通过 | 通过 | MCP 对未完成任务归档返回 INVALID_ARCHIVE_STATE_GROUP；终态归档成功。PAT v2 本次可归档 started，版本行为不能互推 |
| 项目 Page 创建／修改／关联任务 | 通过 | 未测 | detach、archive、delete 清理通过 |
| 附件上传与读取 | 实际 4664 byte 回读通过 | 未测 | MCP upload_from_url 元数据 is_uploaded=false，但实际 read 成功；完整 PAT upload／confirm 链路不标记通过 |
| Work item types、Milestones | 未测 | GET 返回 200 | 只证明读取；不证明付费功能写入或 UI 可用 |
| Plane → GitHub webhook 实时同步 | 未测 | 未测 | 需要公网接收器或轮询，纯 Actions 不提供接收服务 |

## GitHub 事件的端到端结果

下列事件均有私有运行记录；表格保留观察结果，具体运行标识不公开。

测试 PR 绑定隔离项目中的测试任务，使用实际项目状态 ID 和 legacy manual completion 规则：

| 真实事件 | Plane 回读结果 |
| --- | --- |
| 创建 draft PR | 切到本项目实际 started 状态 |
| ready_for_review | 切到已明确指定的自定义待验收状态 |
| close，未合并 | 保持状态 |
| 已手动设为 completed 后 reopen PR | completed 保持，state_changed=false |
| 恢复待验收后合并测试 PR | 记录 merged；保持待验收，未自动完成 |

整个 PR 生命周期评论始终一条，重复事件保持同一评论 ID 和 external key；实际标识已移除。最终文字为“Code merged; manual acceptance is still required.”

测试 Issue 的隔离脚本显式配置“open → todo、closed → completed”，仅用于验证事件能力，不是产品默认策略：

| 真实事件 | 结果 |
| --- | --- |
| Issue opened | 创建一个测试任务，实际 UUID 已移除 |
| Issue edited | 更新同一任务标题／正文 |
| comment created | 创建 Plane 评论 |
| comment edited | 更新同一评论；回读一条，正文为 version two，实际 UUID 已移除 |
| Issue closed | 同一任务切到显式配置的 completed |

## 暴露的接口差异

第一轮验证的 workflow 显示 success，但其中有失败断言；当时探测器尚未把失败项传递为非零退出码。不能把此轮所有能力写成通过。之后修正退出码并分项复测，保留失败运行供审计。

Cycle／Module 初测 GET `/{id}/work-items/` 返回 405，原因是探测器选错读取端点；membership 写入用 POST，读取应筛选项目任务。修正后的运行已验证加入和解除；此轮 workflow 仍因标签回读断言失败而为 failure，不应抹去该信息。[Cycle membership](https://developers.plane.so/api-reference/v2/cycles/manage-cycle-work-items)、[Module membership](https://developers.plane.so/api-reference/v2/modules/manage-module-work-items)

v2 PATCH 空 `label_ids`／`assignee_ids` 返回 200，但随后 GET 的 ID 数组仍返回旧值。延迟后读取、v2 aliases 空数组、v1 PATCH 后再读 v2 ID 数组也复现同样现象；这些运行的原始记录未公开。官方契约要求空数组清除集合。[Update work item](https://developers.plane.so/api-reference/v2/work-items/update-work-item)

为区分写入失败与读数据差异，保留独立任务，**只执行一次 v2 PATCH 空数组**。同一个 runner 随后读 v2 得到旧 ID 数组，读 v1 得到 `labels: []`／`assignees: []`；另用 MCP 读取也为空。因此清除写入实际成功，v2 关系回读与 v1／MCP 不一致。后续 expanded 回读也保留旧关联，该断言运行明确为 failure，不能把 expand 作为已验证的修复办法。缓存、物化字段或序列化的具体服务端原因尚未确认，不能推定为套餐限制，也不能反复写入“修复”。

## 验证边界与工程决定

- 已验证普通自有仓库 PR／Issue／评论事件；fork、Dependabot、review、CI 完成、release／deployment 等事件尚未逐一实测。
- 只验证顺序重放，没有证明并发 upsert 唯一性、跨仓库状态排序或无限重试可靠。
- 原生 Pro 集成未实装验证；其套餐及能力声明来自官方资料。
- PAT 有创建者权限，本次以 Owner 验证；未测 Guest／Member、权限失效、SSO 或自托管版本。
- 不声明与官方双向同步完全等价。反向同步需额外服务／轮询、字段归属、防回环与权限验证。
- GitHub 私有仓库 runner 使用 owner 的共享免费额度，不保证无限免费。[Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- 后续采用 [同步模式设计](sync-provider-design.md)：已配置原生集成可以不装 Actions；Free 可用 Actions；同类事件只由一个执行器写状态。

## 历史证据摘要与清理

最终全量验证完成（原始运行记录未公开）：26 项结果，25 项 pass、1 项已明确记录的 v2 关系回读 limitation，无失败项；数字包含认证、清理和付费能力的只读检查，并非 25 个产品功能。v2 清除后的集合用独立 v1 读取确认，没有重复 PATCH 来掩盖差异。

本地忽略目录 `.plane-devflow.local/capability-probe/` 保存 redacted OAuth receipts、PAT summaries 与运行元数据；GitHub 私有测试仓库保留可复现脚本、提交、PR、Issue 和 Actions 日志。不会把 API key 或真实业务数据提交进验证文档。

探测器创建的 REST 临时任务／标签／Cycle／Module 已逐项 DELETE 并 GET 确认 404，所有轮次 cleanup_failures 为空。OAuth 创建的测试 Page 已 detach／archive／delete；临时测试项目已删除，项目列表确认不存在，其任务、Cycle、Module 等不再保留。删除后单项目读取返回 403，而非 404，清理确认以 DELETE 成功和列表中不存在为准。

测试仓库四个 workflow 均已 disabled_manually，`PLANE_API_KEY` Secret 已删除并读取确认 Secret 列表为空；私有测试仓库已归档，保留脚本／运行记录供审计。Secret 删除不会撤销 Plane PAT，用户可在 Plane 的 Personal Access Tokens 删除这枚临时 token。后续复测需恢复测试资源并重新配置专用 Secret，不能直接复用已清理的项目 ID。

该次验证的代码基线通过 83 项 unittest；这只覆盖当时已有实现，不能证明当时尚未实现的 native provider 切换。v0.4.2 的后续回归与安装结果见 [版本验证记录](validation-0.4.2.md)。
