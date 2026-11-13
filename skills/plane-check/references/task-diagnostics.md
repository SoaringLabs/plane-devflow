# Read-only task diagnosis

Use this mode when asked for a named task's status, blockers, recovery position or partial delivery. Resolve the task explicitly from trusted user context and the mapping. Diagnose first; a status request does not authorize repair, merge, completion or compensating writes.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py task-status PROJECT-123 --repo /absolute/repository
# Only when the user requests current remote facts or explicitly authorizes a refresh:
python3 /absolute/plugin/scripts/plane_workflow.py task-status PROJECT-123 --repo /absolute/repository --refresh --workitem-file /tmp/live-task.json
```

The default reads local Git, shared task/checkout/handoff receipts and any existing sync-health cache. It makes no network/authentication request and writes no cache/checkpoint. It can inspect the task's recorded directory from another registered worktree without switching branches. An unavailable/differently mapped directory remains unknown; it is never rebound. Caller and task directory/branch/head are reported separately.

`--refresh` explicitly reads GitHub configuration metadata and the bound primary PR/required checks. It bypasses the routine 24-hour metadata cooldown by explicit request, without writing a cache or dispatching a connection workflow. It does not fetch Git, change branches or call Plane. Repeated default diagnosis remains offline; avoid repeated explicit refresh without a reason. Network/auth/CLI failure keeps local facts and marks remote evidence unknown.

For current Plane status, use the host's connected MCP read tools, then supply the normalized five-field snapshot documented in [task execution](task-execution.md#gates-and-live-completion-facts). The task/project must match and the observation must be within five minutes. Missing tools or a stale/wrong snapshot remain unknown. The helper does not acquire credentials or promote a stored writeback declaration into a current service readback.

Report the concise `summary`, then relevant `blockers`, `limitations` and `next_actions`. Sections distinguish requirements/check freshness, PR/CI, live Plane task, declared delivery writeback, scoped acceptance/merge declarations, environment ownership and historical local handoff. A successful process exit means diagnosis rendered, not that a delivery gate passed. Local gates are evidence checks only, not overall remote readiness or permission.

Connection verification, an actual PR-event Actions run and confirmed task writeback are separate evidence. Available sync metadata may report a repository-level event run, with its source/time; it does not bind that run to this task or prove task writeback. Missing observations remain unknown. Inspect the actual task-bound event and Plane readback separately. Declared checks are bound to head and brief, not a proof of test quality. Receipt authorization fields cannot authenticate human messages. Original quotes/history are omitted; verify the trusted conversation before consequential actions.

Environment rows are ownership/handoff declarations; diagnosis does not inspect or stop processes. A handoff checkpoint is historical and does not establish current primary-base parity. Use the existing scoped environment and finish-task procedures only after separately authorized completion. Keep remote completion and local handoff distinct.

No task/PR/state/config/auth mutation, dispatch, automatic compensation, background monitoring or cross-machine recovery is added. Diagnose available local receipts in the current host; session portability belongs to the host agent.
