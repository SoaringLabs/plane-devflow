# Setup reference

Resolve `<plugin>/scripts/plane_workflow.py` from the installed Skill. Python 3.10+, Git and a github.com origin are required for repository association; PR operations use the user's GitHub CLI connection. No plugin-specific settings page or custom slash aliases are required.

## Connection and selection

Reuse Plane's official MCP OAuth connection (`https://mcp.plane.so/http/mcp`) and existing GitHub authentication. MCP `workspace/retrieve` identifies the connected workspace. List projects through `project/list`, following the current schema's pagination; retrieve the selected project by ID and read its states. Missing login, wrong workspace and denied project access are different conditions. Reconnect only when needed.

Existing config: offer **检查当前配置** or **重新配置**. New/reconfigure: offer **关联已有项目** or **创建新项目**. Explicit user choices need no repeat question. Recommend matching repository names but leave selection to the user. Creation proposes a name and valid identifier, checks for conflicts, then calls `project/create` within the user's selected creation scope. Do not silently create a different name after conflict. An uncertain response needs inspection before retry. Keep the returned project available for recovery after local failure.

For an empty project, project/state reads prove live access; zero tasks is not an error. New association does not create `In Review` or any other state.

Save actual MCP JSON results in an ignored local directory or temporary location. These are response snapshots, not authorization tokens. Strip tool envelopes to the JSON payload, or use a `{ "result": ... }` wrapper. A project list may be a list or an API `results`/`data` object; combine pages into a complete list first.

Optional formatting helper (returns choices and creation defaults; never auto-binds):

```sh
python3 /absolute/plugin/scripts/plane_workflow.py project-options \
  --repo /absolute/application/repo \
  --workspace-file /tmp/plane-workspace.json --projects-file /tmp/plane-projects.json
```

## Basic association

After retrieving the selected project's actual ID/identifier, run:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py configure \
  --repo /absolute/application/repo \
  --workspace WORKSPACE_SLUG --project-id PROJECT_UUID --project-key PROJECT \
  --base ACTUAL_DEFAULT_BRANCH \
  --workspace-file /tmp/plane-workspace.json --project-file /tmp/plane-project.json
```

Inspect the result, then repeat with `--apply --expected-config-sha256 HASH_FROM_PLAN`. `missing` is the expected value for first setup. Plan mode does not write files or read credentials. Snapshots are checked for workspace/project consistency; actual MCP reads establish access, not the local helper alone.

New config is version 2: project/repository association, `states: {}`, `status_sync: {enabled: false}`, and manual completion preference. No state IDs, API key, Cycle or work item are required. Custom status rules come later. Existing version 1 remains supported with its configured states, completion policy and manual label. A same-project rerun preserves these preferences without forcing schema migration.

Resolve the GitHub base branch from configured mapping, remote default ref or GitHub metadata; do not assume `main`. Completion defaults to `manual` for new mapping. Use `--disable-state-sync` only if requested; it explicitly produces basic version 2. Legacy state parameters remain supported for existing deployments, not required for basic setup.

## Safe reconfiguration

Use the same selected-project command with `--replace` to generate a replacement plan. It reports differences, whether the project changed and `expected_config_sha256`. Cancellation leaves the existing file intact. Repeat reviewed arguments with `--replace --apply --expected-config-sha256 HASH_FROM_PLAN` when applying.

The helper checks the original hash, takes a shared Git metadata lock, backs up original bytes under the common Git directory's `plane-devflow/backups/`, and atomically replaces the mapping. Backups and locks are outside tracked application files. Failed replacement preserves the original file. A changed hash requires a fresh plan, not force overwrite. An identical mapping preserves formatting and creates no needless backups. No auth store or remote Plane object is removed.

Selecting a different project clears old state targets and disables status sync. It preserves repository/base/branch-prefix and completion preferences unless the user changes them. Invalid config can be replaced using the same hash/backup flow. `doctor` reports invalid config without deleting it.

Before applying on an old task branch, use the repository's setup/base checkout or a dedicated setup checkout. Existing task branches/worktrees and PRs keep their original project association; never retarget them to the new project. Old PR bindings are rejected against a different configured project. Report unresolved old work rather than loosening binding validation.

Commit/merge mapping into the intended base branch before creating a new isolated task branch. Full initialization also needs mapping and sync files in the GitHub default branch. Prepare the concrete configuration change first. Creating a setup PR is within a request to configure GitHub synchronization; merging that PR needs the user's merge authorization. Do not mix unrelated application changes into it.

## Choose native or Actions synchronization

Full initialization includes verification of the selected native or Actions integration. Actions is the default; its steps follow below. Project association alone is partial setup. A user may temporarily defer unavailable credentials/permissions; keep successful configuration, explain the missing capability and offer **继续配置 GitHub 后台同步** on subsequent invocations.

After association, run:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py check-github --repo /absolute/application/repo
python3 /absolute/plugin/scripts/plane_workflow.py setup-github --repo /absolute/application/repo
```

The second command plans a repository-local workflow plus two bundled standard-library Python scripts. Repeat with `--apply` to prepare the files. No published plugin repository, extra service or invented Action SHA is required. Existing differing files require a reviewed upgrade:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py setup-github --repo /absolute/application/repo --upgrade
# Inspect the reported differences, then repeat:
python3 /absolute/plugin/scripts/plane_workflow.py setup-github --repo /absolute/application/repo \
  --upgrade --apply --expected-files-sha256 HASH_FROM_PLAN
```

Plugin and sync-bundle releases are independent. Inspect read-only `setup-progress` before planning an upgrade: supported older bundles can remain ready, and an optional update alone grants no changes. See [bundle maintenance](recovery.md#sync-bundle-maintenance).

The plan binds every destination plus the current config. A stale hash fails before writes. Original differing bytes are backed up in Git metadata; the mapping and unrelated files are preserved. Plugin updates do not silently update business repositories.

The workflow uses pinned `actions/checkout` to read only synchronization files from `github.sha`, the trusted default-branch commit for `pull_request_target`; it executes no PR head code or project build scripts. It handles PR opened/edited/updated/reopened/review-ready/draft/closed events and has a read-only `workflow_dispatch` connection check. Both config versions are supported: version 1 uses existing state targets and acceptance rules; version 2 records PR events without state transitions. Keep these capabilities separate in the report.

Inspect repository Actions permissions and applicable event policies. GitHub public repositories can block `pull_request_target` through event policy; explain the specific restriction if present rather than claiming a connection check proves event delivery. Leave unrelated security policies intact. See [GitHub event security and policies](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).

Follow [the credential guide](credentials.md) when the Secret is missing: first open Plane and guide PAT creation, then open the mapped repository's GitHub Secret form, then verify metadata. Do not skip directly to “put your PAT in GitHub” or make the user discover the creation page. Browser/computer use is optional host assistance; it is not a hard plugin dependency. The interactive `set-secret` command remains an alternative only when the user chooses terminal entry. Account OAuth is preserved and is not the runner credential.

Prepare the mapping/workflow/scripts as a setup change in an isolated branch if the checkout has unrelated work. Explain the concrete changes. A workflow saved locally or in an unmerged PR is **not active**. Once the change is in the default branch, run:

```sh
gh workflow run plane-devflow.yml --repo OWNER/REPO --ref ACTUAL_DEFAULT_BRANCH
python3 /absolute/plugin/scripts/plane_workflow.py check-github --repo /absolute/application/repo
```

Wait for the new dispatch run to finish; correlate it to the current default SHA. The connection check reads the Plane project/states using the actual Secret and validates configured targets. It never changes work items/comments. `check-github` checks recognized compatible sync-bundle fingerprints, config equality, workflow activation, Actions enablement, Secret presence and the latest connection run at that SHA; unknown permission/API results remain incomplete. A failed newer check supersedes an older successful check. Report **连接验证通过，PR 事件回写尚未实测** until a real linked PR run has been inspected; read access alone does not prove write access. Do not create/merge a test PR or mutate Plane tasks solely to claim verification without user scope.

Use this incomplete-setup explanation, adjusted to the actual blocker:

> **初始化尚未完成：GitHub 后台同步未配置或未就绪。**
>
> GitHub 上创建、更新或合并 PR 后，这些事件无法自动同步到 Plane，也不会触发对应的任务状态转换。当前 agent 内的 Plane 操作仍可使用；GitHub 上发生的变化需要回到当前 agent 中检查并同步。
>
> 已保存当前配置，可以稍后选择“继续配置 GitHub 后台同步”。

If the workflow exists but verification failed, say automatic sync is **not verified** and identify the failure rather than asserting every event is definitely blocked. If only state synchronization is disabled, say events can update PR records while task states stay unchanged. Preserve the user's completion policy: merge evidence cannot replace manual acceptance.

## Native mode

Use `configure --sync-provider native` with the normal selected-project and replacement/hash safeguards. Native requires a supported official integration plan **and an actual connection**, not a plan name alone. `setup-github` skips file generation and reports no Secret requirement. `check-github` checks an exact-config observation receipt, without calling Actions permissions, Secrets or workflow APIs. The plugin does not have an official integration discovery API.

Inspect the official GitHub organization installation, repository/project mapping, and status rules through authorized UI access, or obtain explicit user confirmation when that UI cannot be read. Check how merge completion and manual acceptance actually work; local completion flags cannot control the official service. If native rules conflict with required acceptance, explain the difference and propose Actions. Never infer successful mapping from a paid plan or write a receipt without observation/confirmation.

Create the following JSON in a temporary file using the actual observation. `config_sha256` is the canonical configuration hash `native_config_sha256` shown by native `check-github`, not `doctor`'s original-byte replacement hash:

```json
{
  "config_sha256": "CANONICAL_HASH_FROM_CHECK",
  "workspace": "ACTUAL_WORKSPACE",
  "project_id": "ACTUAL_PROJECT_UUID",
  "repository": "ACTUAL_OWNER/REPO",
  "repository_mapped": true,
  "workflow_rules_verified": true,
  "overlapping_actions_disabled": true,
  "source": "user_confirmation",
  "observed_at": "ACTUAL_ISO_TIME_WITH_TIMEZONE"
}
```

Use `source: plane_ui` only for a UI observation you actually performed. Plan and apply `record-native --repo /absolute/application/repo --evidence-file /tmp/observation.json [--apply]`. The receipt stays under the common Git directory, outside committed application files. Then run `check-github`; report its source and observation time. Configuration changes invalidate the receipt; official settings changed outside the plugin require a new check/receipt. A receipt establishes observed configuration, not a real event writeback. Actual PR writes remain separately reported.

Switching modes must also resolve the previous writer. Disable the plugin workflow before enabling official lifecycle rules, or disable the overlapping official rules before Actions. Do not enable both for the same PR transitions. An active old workflow/config replacement is blocked by the helper until the reviewed disabling change is resolved.

## API routing

The optional committed section is `"sync": {"provider": "actions", "api_version": "v1"}`. Absence means Actions + v1, including existing configs; a same-project rerun preserves legacy states and completion settings. `configure --api-version v2` selects explicit v2 task/state routing when needed; comment upsert always uses v2. Fresh v1 safety reads still protect against observed stale expanded v2 relations. v1/v2 API routing is independent of config schema versions 1/2. Rate limiting does not trigger an API-version fallback; long Retry-After delays end the run for a later retry.

## Existing event workflows and pinned Actions

Replacing config while `.github/workflows/plane-devflow.yml` exists is blocked. Also inspect the relevant base-branch workflow: an older pinned Action cannot read version 2. Resolve disabling/removing the old workflow through a reviewed GitHub change first; do not delete it merely because the user selected reconfigure. Ensure old events cannot apply old mapping while association changes. This stage does not automatically rewrite active event workflows.

The older `configure --action-source owner/repository@FULL_40_CHARACTER_COMMIT_SHA` remains a legacy integration path for unchanged version 1 mappings. Only use an actual published SHA. Prefer the bundled workflow for new setup; migrating an existing pinned workflow needs a reviewed change. The readiness helper conservatively verifies the bundled files; it does not certify a different custom/pinned workflow without separate review.

Receive the PAT through GitHub Secrets or a human-operated interactive terminal:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py set-secret --repo /absolute/application/repo
```

Input is hidden and sent through stdin. Personal/organization ownership does not bypass permissions or SSO. Never put the token in chat, code, arguments or MCP response snapshots.

Report HTTP restrictions, external writes and actual workflow runs separately. Offline tests do not establish account write permission. Self-hosted OAuth and GitHub Enterprise remain outside this stage.
