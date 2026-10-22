# Plane DevFlow architecture and scope

Plugin distribution is portable `plugin.json`, `mcp.json`, `skills/` and bundled references/scripts. The repository root also contains a local marketplace and the public product composite GitHub Action. Codex executes Skill instructions; deterministic scripts handle Git/config/reporting and REST lifecycle synchronization.

Project selection/creation and safe repository reassociation use the official Plane MCP through the setup Skill; local helpers consume response snapshots and never replace account authorization. Start also drafts a project's first task list and creates the specifically approved items through MCP. Saved batches and separate active/archived readbacks reconcile lost replies before any missing creation. General task/Cycle/Module management, custom action rules and background context inference are outside scope.

New setups use basic config version 2: it stores no state targets and preserves task states. Legacy config version 1 retains its configured lifecycle rules; subsequent state-transition statements below apply only to that profile. Native transitions remain owned by the official integration.

Version 0.4.0 supports native and Actions synchronization. Native readiness uses an exact-config receipt from actual UI observation or explicit user confirmation, stored in Git metadata; it is not automatic integration discovery. Native skips repository workflow generation and runner Secrets, and suppresses overlapping Start/Deliver/PR state updates. Actions keeps the following full-initialization checks. `setup-github` prepares a small repository-local workflow pinned to a formal product Action commit; its manifest binds version and source. Historical copied layouts remain readable through their frozen catalog. `check-github` reads Secret names (never values), compares config and sync files at one immutable default-branch SHA, checks Actions/workflow activation and the latest connection run for that SHA. Unknown or failed evidence remains partial and resumable; local `doctor` alone cannot certify remote readiness. Read-only dispatch validates the PAT, project and state targets; real PR writes and event-policy restrictions are reported separately.

Reconfiguration is explicit: plan differences, verify the reviewed original SHA-256, lock in shared Git metadata, back up original bytes there, then replace using an fsynced temporary file and atomic rename. Plan/check operations leave config untouched. A different project drops old state targets; old task branches are not retargeted, and mismatching PR bindings remain rejected. Existing event workflows block replacement, including a known workflow in the local base commit. Resolve active remote workflows first; no distributed lock with GitHub/other editors is claimed.

| Responsibility | Owner |
| --- | --- |
| Task requirements and human acceptance | Plane work item and user |
| Implementation and repository checks | Codex plus repo instructions |
| Code state, review and merge evidence | Git/GitHub |
| Stable project/repo/state mapping | `.plane-devflow.json` in each business repo |
| Interactive credentials | Official Plane MCP OAuth / existing GitHub CLI |
| Unattended synchronization credential | Per-repository GitHub Secret `PLANE_API_KEY` |

MCP uses Plane's official OAuth endpoint. The background workflow uses public Plane REST v1 by default and v2 for atomic comment upsert, with its distinct PAT. No plugin-owned backend or credential proxy is introduced. Personal and organization repositories use the same mapping. This implementation supports github.com and Plane Cloud; HTTPS REST origins are configurable for tests/future expansion, but a full self-hosted OAuth/GitHub Enterprise integration is not claimed.

Git side effects are opt-in `--apply`, use argument arrays, and do not reset user changes. New branches require mapping already present in the base commit. Worktrees share the original Git common directory and preserve unrelated changes. Existing PRs are reused, while merged/closed task branches require deliberate follow-up decisions.

The generated workflow pins the public Action to the product’s full release commit, passes trusted default-branch `github.sha`, fetches the latest PR snapshot, then reads config at that trusted configuration SHA. Common Python implementation stays in the Action payload. It never executes PR head code or project build scripts. Manual connection dispatch is restricted to the default branch before credentials are used. The older composite Action still reads trusted PR base config when no workflow SHA is supplied. `pull_request_target` supplies base-repository permissions/Secrets; this design still assumes trusted base maintainers and deliberate primary-task references. Config URLs determine where the Plane PAT is sent, so reviewing base config is part of trusting this integration.

Primary task matching accepts `[PROJECT-123]` plus an optional exact binding. Generated reports always include the binding. Cross-repository, cross-workspace/project and multiple-primary references are rejected. One task / one primary PR is the v1 contract, not a multi-PR completion aggregator.

State transitions preserve terminal groups and do not move a configured review task back to development. Merging writes Done only under `on_merge` without the manual label. A merged task under manual policy stays review. Closing an unmerged PR makes no state transition. The lifecycle comment is upserted by `(external_source, external_id)`; per-PR concurrency serialization reduces duplicate writes. No distributed exactly-once guarantee is claimed.

Network calls reject redirects to avoid forwarding credentials elsewhere. API error bodies and Git remotes are not logged. Read operations retry transient failures; ambiguous network failures on writes require inspecting current state before replay. Read retries and retryable rate limits are bounded; ambiguous POST/PATCH/DELETE server failures are not automatically replayed. State writes and comment writes are separate calls; if the second fails, rerun after checking the already changed state.

Validation separates offline behavior, mocked HTTP contracts, real OAuth/read checks, and live external write/Action runs. Only checks actually executed should be reported as passed. An installed plugin can require a new Codex chat to refresh available tools.

Primary references: [Codex plugins](https://developers.openai.com/codex/plugins/), [Plane MCP](https://developers.plane.so/dev-tools/mcp-server), [Plane API](https://developers.plane.so/api-reference/introduction), [GitHub pull_request_target](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target).

Explicit v2 routing retains a fresh v1 state/label safety read. Normalization resolves UUID relations using complete collections before terminal/manual-acceptance decisions. API retry delays are bounded without shortening Retry-After. Reviewed bundled-file upgrades bind file/config hashes and preserve old bytes in Git metadata.

## Task execution receipts (0.5.0)

Start and Deliver now require a brief/design decision, scoped verification and self-review before ordinary PR delivery. task_progress.py stores per-task version 1 receipts in shared Git metadata, with project/repo/base identity, expected-content digest, atomic updates, previous snapshots, and current evidence gates. It performs no remote mutations or task state transitions. User-source fields are declarations verified by the Skill against original human context; they are not cryptographic proof or permission by themselves.

Review checks bind current requirements and HEAD; report stamps also bind the receipt digest. A Draft can carry blockers, while ordinary delivery checks current evidence before pushing. Merge and completion read live GitHub PR/required checks; completion additionally requires a fresh normalized Plane MCP task/label snapshot. Exact PR head remains the evidence version after squash merging. Schema versions 1/2, binding protocol 1, existing completion policies and native/Actions ownership are preserved; custom action/state rules remain unimplemented.

One product release covers local skills/helpers and the public Action. Installing files alone changes only the local installation. The [unified upgrade flow](../plugins/plane-devflow/references/product-upgrades.md) coordinates fixed source staging, the original installation channel, an isolated project PR, activation and fresh connection evidence. Its independent non-secret record survives installation replacement and host refresh. Projects retain their historical deployment until its upgrade PR is merged; old copied layouts are recognized without automatic replacement. Agent behavior and semantic coverage still require representative conversation and actual product acceptance; deterministic tests validate receipt/gate behavior, not language understanding.

## Checkout guards and handoff (0.6.0)

`checkout_workflow.py` stores task checkout bindings and local handoff checkpoints in separate directories under shared Git metadata, keyed by the same repository/project/base/task identity as receipts. Preparation captures an immutable starting commit; `task-context` plans/applies an authorized path scope using an inspected SHA-256 and the existing metadata lock. Implement/review/merge gates check directory, branch, cumulative file differences, history continuity and early integration into the known base. Delivery rechecks context before pushing, including Drafts. File matching cannot replace semantic diff review.

`finish-task` requires fresh complete-gate evidence and completed-task readback. It locates the primary checkout, preserves ownership of unrelated branches/worktrees, fetches the configured origin base, verifies inclusion of the merged PR, rejects local unique history, switches and pulls with `--ff-only`, then verifies clean local/remote parity. Local handoff status is independent of Plane completion; retries revalidate live evidence and update only local Git/checkpoint state. These helpers perform no Plane state/comment writes and leave state/provider configuration unchanged.

## Readiness evidence and task diagnosis

`sync_health.py` keeps optional non-secret metadata observations in shared Git metadata, keyed by the full mapping digest. Success and failure both start a 24-hour routine-probe cooldown. Historical connection evidence expires after 24 hours; expiry never dispatches a connection test or blocks independently authorized development. `doctor --offline` makes no authentication/network requests. Explicit refresh can bypass cooldown; real PR events remain independent of local probes. Deployment uses one product version; historical bundle versions remain legacy layout identifiers only.

`task-status` composes existing checkout, receipt, gate, doctor and sync-health readers. Its default is local Git/receipts plus any existing cache, with no network or cache writes. Explicit refresh reads a bound GitHub PR/required checks and remote setup metadata; Plane facts come from a task/project-bound host-MCP snapshot no older than five minutes. No helper credential or business-state mutation is added. Caller and selected task directories remain distinct; reads never switch a branch.

The output separates local check declarations, current remote facts, pending writeback, human acceptance/merge declarations, environment ownership and historical handoff checkpoints. Connection-test success cannot stand for an actual PR event or writeback. A checkpoint cannot establish current base parity or process liveness. Original human messages still govern consequential actions.

## Capability and validation inventory

The [capability matrix](capabilities.md) separates implemented contracts, deterministic tests, synthetic decision/execution evidence, native discovery and scoped real-service observations. Model execution evaluations use disposable repositories, synthetic stdio MCP and actual tool-effect assertions; CI does not consume model credentials. They do not certify production service contracts or universal host compatibility.

Conversation/session transfer belongs to the host agent. Cross-chat use of local receipts is supported within available trusted context; a cross-machine session service is not a skill requirement. Multi-host discovery and automatic credential adapters remain ongoing compatibility maintenance. Public scope remains three skills and one primary PR per task.
