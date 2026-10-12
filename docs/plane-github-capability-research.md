# Plane 免费方案与 GitHub Actions：能力资料核对

核对日期：2026-10-10（Asia/Shanghai）。来源限 Plane 与 GitHub 官方文档。本记录没有读取用户任务、使用凭据或调用外部写入接口；实际账号／套餐和端点验证须看单独的验证记录。

本文保存核对当日的资料，不保证后续套餐、计费或事件政策保持不变。实际接入时应重新核对引用的官方文档和账号设置。

## 结论与证据边界

可以把 GitHub Actions 作为 GitHub → Plane 的后台同步执行器，并让 Codex 插件负责配置、开发操作和关联规则。官方已公开的 REST 能力覆盖任务、评论、链接、标签、负责人、Cycle、Module 和附件，扩展范围不必限于 PR 生命周期。[Plane API v2](https://developers.plane.so/api-reference/v2/introduction)

但“有 API 文档”不等于“该免费工作区可用”。Plane 会对付费或未启用能力返回 `402 payment_required`，权限问题则可能返回 `403`，部署版本不同还可能没有相同端点。本记录中“文档已确认”仅代表接口契约存在，不能写成“免费套餐实测通过”。[Plane errors](https://developers.plane.so/api-reference/v2/errors)

Plane 官方 GitHub Marketplace 明确列出 Pro、Business、Enterprise，并覆盖 Cloud／Self-hosted。因此免费用户的路径应独立使用 API，而不要求启用官方 GitHub 集成。定价页列明 Free 包含 Projects、Work Items、Cycles、Modules；PAT／webhook 的具体 Free 权限仍需账号实测。[GitHub Marketplace](https://plane.so/marketplace/github)、[Plane pricing](https://plane.so/pricing)

## 认证与部署

- **REST PAT**：`X-Api-Key`，以创建者身份执行，继承其全部权限，没有只读 PAT 或 OAuth scope 限制。首次检查可请求 `/api/v2/users/me/`。应由用户创建专用 token 并放入 GitHub Actions Secret，不能从当前会话已有 OAuth 连接推定 PAT 已存在。[Authentication](https://developers.plane.so/api-reference/v2/authentication)
- **REST OAuth**：`Authorization: Bearer`，适合插件成为多用户应用后按同意授权；需处理 scope 和 token 生命周期。[Authentication](https://developers.plane.so/api-reference/v2/authentication)
- **MCP OAuth**：交互客户端连接 `https://mcp.plane.so/http/mcp`，授权时绑定工作区。MCP PAT 另有 MCP headers，与 REST PAT header 不同。MCP 能操作任务，并不能证明 Actions 的 REST 凭据可用；自托管 Community Edition 的 MCP 文档建议 stdio 模式。[MCP server](https://developers.plane.so/dev-tools/mcp-server)
- Cloud REST base 为 `https://api.plane.so`；自托管使用实例 URL。v2 路径以 `/api/v2/` 开头并带尾斜线；v1 仍存在。实际部署应探测版本，不要只更换字符串。公开 live schema 为 `/api/v2/schema/`。[API v2 introduction](https://developers.plane.so/api-reference/v2/introduction)

## 扩展能力矩阵

以下均为**官方文档已确认，免费工作区未在本记录实测**。

| 能力 | 官方契约／限制 | 适合的验证目标 |
| --- | --- | --- |
| 任务 CRUD、归档、查找 | 项目 UUID 路由读写；人类标识符有独立 workspace 只读查找；有 upsert／bulk 接口 | 新建隔离测试任务，按 UUID／标识符读取，修改再清理 |
| 状态、优先级、标题、日期 | PATCH 部分更新；`state_id` 属于该项目；状态规则可返回 `workflow_transition_denied` | 选择实际状态 ID，往返更新并确认回读 |
| 标签、负责人、父任务 | `label_ids`／`assignee_ids` 全量替换，非追加；父任务同 workspace，可跨 project | 测试新增／删除集合元素，父子关联／解除 |
| 评论 CRUD／upsert | 支持 HTML、external source／id、visibility；普通 create 不去重 | 相同 external key 顺序 upsert，两次调用仍单条 |
| PR／文档外链 CRUD | Links API 有 URL、title、metadata，没有官方 link upsert | 按规范化 URL 查重，更新标题，检查重放不重复 |
| Cycle | CRUD／upsert、增删任务、transfer；owner 在 v2 只读 | 创建临时 Cycle、加入／移除任务、迁移后回读 |
| Module | CRUD／upsert、增删任务；members 在 v2 只读，归档／取消归档目前仅 v1 | 临时 Module 关联与解除；不承诺成员写入 |
| Activity | 任务审计活动仅 list／get，append-only | 检查状态／评论操作是否生成对应活动 |
| 附件 | 创建 upload、确认 upload、读取、删除 | 小文件完整上传／回读／删除；仅创建记录不算上传成功 |

来源：[Work items overview](https://developers.plane.so/api-reference/v2/work-items/overview)、[Update work item](https://developers.plane.so/api-reference/v2/work-items/update-work-item)、[Comments overview](https://developers.plane.so/api-reference/v2/work-item-comments/overview)、[Links overview](https://developers.plane.so/api-reference/v2/work-item-links/overview)、[Cycles overview](https://developers.plane.so/api-reference/v2/cycles/overview)、[Modules overview](https://developers.plane.so/api-reference/v2/modules/overview)、[Activities overview](https://developers.plane.so/api-reference/v2/work-item-activities/overview)、[Attachment upload](https://developers.plane.so/api-reference/v2/work-item-attachments/create-attachment-upload)、[Confirm attachment](https://developers.plane.so/api-reference/v2/work-item-attachments/confirm-attachment-upload)。

Cycle／Module 关联是各自 `/{pk}/work-items/` 的 POST，body 使用 `add`／`remove` UUID 数组；不要假定把这些 read relation fields 填进任务 PATCH 就能修改。[Cycle membership](https://developers.plane.so/api-reference/v2/cycles/manage-cycle-work-items)、[Module membership](https://developers.plane.so/api-reference/v2/modules/manage-module-work-items)

## 幂等、重试与反向同步

Work item 与 comment 的 upsert 以 `(external_source, external_id)` 匹配，**仅顺序写入安全**；同 key 并发可能各自创建一条。同步执行器应对资源 key 串行化，且跨仓库更新同一任务还需共享协调。普通评论 create 不自动去重；links 需自行持久关联或查重。[Work item upsert](https://developers.plane.so/api-reference/v2/work-items/upsert-work-item)、[Comment upsert](https://developers.plane.so/api-reference/v2/work-item-comments/upsert-comment)、[Comment overview](https://developers.plane.so/api-reference/v2/work-item-comments/overview)、[Links overview](https://developers.plane.so/api-reference/v2/work-item-links/overview)

`429` 遵循 `Retry-After`，不要把 v1 文档的 60 requests/min 当成所有 v2 token 类别的固定额度；v2 文档按 token 类别分桶。对 401／402／403／409 分别处理，不应无限重试。[Plane errors](https://developers.plane.so/api-reference/v2/errors)

Plane webhook 可提供 workspace 级事件，只有 Owner／Admin 管理；接收端必须公网可达并验证原始 body 的 HMAC-SHA256。v2 `event_id` 跨重试稳定，可去重；`delivery_id` 每次不同。服务端失败指数退避，5 次失败禁用 webhook；4xx 不重试。免费工作区 webhook 配置与交付仍需实测。[Plane webhooks](https://developers.plane.so/dev-tools/intro-webhooks)

**工程推论**：纯 Actions 是按 GitHub 事件运行的流程，不是常驻 Plane webhook 接收服务。Plane → GitHub 实时反向同步还需要接收桥梁，再调用 `repository_dispatch`；或增加定时 API 轮询，接受延迟。不能直接把带 Plane 签名的 webhook URL 填成 GitHub dispatch API，因为后者需要 GitHub 认证与规定的 body。[Actions events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

## GitHub 免费额度与触发条件

GitHub Free／Free for organizations 的私有仓库标准 runner 包含每月 2,000 分钟、500 MB artifacts；cache 是每仓库 10 GB。公开仓库标准 hosted runners 免费，larger runners 始终收费。额度属于仓库 owner，与现有 CI 共用；没有有效付款方式时，超额运行被阻止。有付款方式时须检查预算，不能宣称私有仓库无限免费。同步推荐标准 Ubuntu，不生成不必要的 artifacts／cache。[Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Actions 可监听 PR／review、issues／comments／labels、release、deployment status，也支持手动和 repository dispatch。不同事件有默认分支存在要求；PR 默认并不触发所有 activity types；GitHub Actions 自己生成的 check_run／check_suite 有防递归限制。CI 完成宜使用 `workflow_run` 或在原 CI 最后显式调用，而不是只监听 check_run。[Actions events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

Fork PR 的 `pull_request`／review 流程通常没有仓库 secrets；`pull_request_target` 能拿 secrets，但必须只执行可信 base 代码，禁止 checkout／执行 PR 代码。官方最新文档还声明：部分公开仓库的默认 event policy 目前 evaluate，**2026-11-02 起 enforce**，届时会阻止未显式允许的 `pull_request_target`。安装检查需检测 repository policy，不能保证旧 workflow 永久可运行。[Secure pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)

`GITHUB_TOKEN` 触发的事件通常不产生后续 workflow；dispatch 是例外，当前文档另外列出 opened／synchronize／reopened PR 可以进入需要批准的运行。不要依赖 GitHub bot 写入自动触发下一段同步，必要时显式 dispatch，并做防回环。[GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)

## 建议的实测顺序

1. 确认目标工作区确为 Free、非 Business 试用；明确实际 REST 版本、PAT 身份与项目权限。
2. 用专门测试任务覆盖矩阵中的基础读写、集合替换、幂等重放、Cycle／Module 和清理；附件以实际 byte 上传成功为准。
3. 分别记录“仅文档支持”“MCP 成功”“PAT REST 成功”“GitHub Actions 端到端成功”；后两者不可由前两者代替。
4. webhook 反向同步、fork／Dependabot PR、跨仓库并发作为独立验收项，不因普通 PR 测试通过而宣称完成。
5. 产品提供 native／actions 两种模式；同一类事件只交一方写状态。状态映射明确配置 ID，并允许保持当前状态，不由套餐决定状态语义。
