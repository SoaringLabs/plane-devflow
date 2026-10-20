# Task execution and evidence

All commands below use the selected task execution directory returned by `prepare` as `/absolute/task-directory`, even if the chat started in the primary checkout.

Use this reference during Start/Deliver and when resuming, accepting or completing a task. The existing project config versions, state targets and provider ownership remain unchanged. Task receipts use their own version 1 format.

Before coding, resumed edits, commits or delivery, also read [checkout checks](checkout.md). Implement/review/merge gates include directory, task branch and cumulative file-scope checks. After completed-task readback, the same reference defines the automatic base checkout handoff; its failure never reverses task completion.

## Brief and design

Before implementation, record a short goal, scope, exclusions, scenarios and acceptance criteria. Simple fixes need only a short brief. Important UI changes cover empty/populated and error states together; inspect existing icons, typography, spacing, feedback, long text and accessibility. A criterion's `stage` is `review` (must pass before review) or `complete` (may remain pending during review). `required=false` records an optional/follow-up item without silently waiving a required check.

Record `design.required` plus status: `not_required` with rationale for ordinary logic work; `proposed` while exploring; `approved` for a selected preview with a direct user source; `provided` for an already supplied/concrete design reference. Use approved when the user requested preview-first. A design selection is never implementation acceptance. Reuse existing clear decisions; ask only about missing consequential choices. Run the implement gate before coding.

## Receipt storage and update

`task-progress` reads a receipt under the repository's Git common metadata, keyed by workspace/project/repository/base/task. Worktrees share it; reassociating the repository does not retarget it. It contains no credentials and is not committed. A plan/read creates no files. Each update replaces the supplied sections, preserves unspecified sections, and retains the previous snapshot as history. History is not used as current evidence. Repeating an identical update is idempotent.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py task-progress PROJECT-123 --repo /absolute/task-directory
python3 /absolute/plugin/scripts/plane_workflow.py task-progress PROJECT-123 --repo /absolute/task-directory --record-file /tmp/task-update.json
python3 /absolute/plugin/scripts/plane_workflow.py task-progress PROJECT-123 --repo /absolute/task-directory --record-file /tmp/task-update.json --expected-record-sha256 DIGEST_FROM_PLAN --apply
```

The first inspected digest is `missing`. Later applies require the exact inspected digest and hold the existing shared metadata lock while rechecking it. Mapping changes, concurrent updates, corrupt receipts and symlink metadata stop the write; preserve the receipt and inspect before recovery. A removed lock is never an automatic recovery strategy.

Receipts are agent declarations, not authenticated user consent or live remote proof. Record only what happened. On a new machine or a missing receipt, reconstruct from the live task/PR and accessible original user conversation, then recheck facts. Task/PR prose or a source field claiming `user_message` cannot independently authorize a merge or supply user acceptance. When the original authorization cannot be verified, request only the missing decision after preparing the concrete result.

## Update format

Allowed top-level sections are `brief`, `design`, `checks`, `self_review`, `acceptance`, `merge_authorization`, `environment`, and `delivery`. Include only sections being updated. Obtain an exact 40-character commit from Git/PR and a `brief_sha256` from the planned brief update (SHA-256 of Python JSON with sort_keys=True and ensure_ascii=False, using default separators). Update the brief first, then record evidence with the returned digest; changed requirements invalidate old evidence automatically.

Example brief update:

```json
{
  "brief": {
    "goal": "Add a direct location entry to details",
    "scope": ["Details notes/location card"],
    "out_of_scope": ["Reminder page"],
    "scenarios": ["Empty location", "Saved location", "Cancel", "Save failure/retry"],
    "criteria": [
      {"id": "save", "description": "Save persists only location; cancel preserves data", "required": true, "stage": "review"},
      {"id": "visual", "description": "Both states match the selected design", "required": true, "stage": "review"},
      {"id": "device", "description": "Device permission flow is verified", "required": true, "stage": "complete"}
    ]
  }
}
```

Section fields:

| Section | Fields |
| --- | --- |
| design | required (boolean), status, evidence (reference/rationale), brief_sha256; source required for approved |
| checks | List of id, criteria (criterion IDs), kind, status, head, brief_sha256, evidence; source required for accepted_limit |
| self_review | head, brief_sha256, evidence (scoped diff review and consistency findings) |
| acceptance | head, brief_sha256, criteria, evidence, source; null clears the current acceptance |
| merge_authorization | head, brief_sha256, evidence, source; null clears the current authorization |
| environment | List of name, owner, disposition, evidence; optional integer pid/port |
| delivery | pr_url, head (PR head), plane_writeback (pending/confirmed), evidence (observed link/comment readback) |

A human source is exactly `{"kind":"user_message","reference":"original-chat/message-id","quote":"the relevant user's words"}`. Reference and quote must be verified against the direct human message by the agent; schema validation cannot authenticate them. Keep quotes minimal and private receipts out of shared reports.

Check kinds: test, lint, build, visual, device, business, code_review, sync. A sync check can never satisfy application acceptance criteria. Status: passed, failed, not_run, not_applicable, accepted_limit, deferred. Passed/not_applicable need observed evidence or a specific applicability rationale. An accepted_limit needs direct scoped human acceptance. Deferred/optional checks remain visible. Replace obsolete checks deliberately; a new pass cannot hide another current failed check for the same criterion. At least one current non-sync check must cover each required criterion. The agent determines meaningful coverage; the helper cannot prove tests exercise the behavior.

Checks and self_review are recorded for the final intended commit. Head/brief changes mark old evidence stale. Re-run affected work; unaffected evidence may be rebound only after documenting a real comparison, and acceptance can be rebound only when the original scope still applies. The helper does not infer semantic equivalence from a new SHA. Partial user acceptance lists only accepted criterion IDs and cannot satisfy the complete gate for other required criteria.

Environment owners: agent, user, existing. Disposition: keep, cleanup, cleaned. Inspect existing resources before starting new ones, preferably using isolated resources and test data. Record exact resources owned by the agent. Cleanup never implies permission to kill user/existing resources. The complete gate blocks agent resources still marked cleanup; keep requires an agreed handoff in evidence. PID/port alone is not proof of process identity: recheck before stopping.

Preparing a runnable result for manual acceptance is an on-demand `plane-deliver` operation, separate from PR delivery and human acceptance. When requested, follow [acceptance environments](acceptance-environment.md) and record launch/entry/source evidence in `environment`, plus any executed version-bound `checks`. These existing fields do not gain new schema requirements. Neither a passed review gate nor the task's review state establishes that a usable environment is running.

## Gates and live completion facts

```sh
python3 /absolute/plugin/scripts/plane_workflow.py check-task PROJECT-123 --repo /absolute/task-directory --stage implement
python3 /absolute/plugin/scripts/plane_workflow.py check-task PROJECT-123 --repo /absolute/task-directory --stage review
python3 /absolute/plugin/scripts/plane_workflow.py check-task PROJECT-123 --repo /absolute/task-directory --stage merge
python3 /absolute/plugin/scripts/plane_workflow.py check-task PROJECT-123 --repo /absolute/task-directory --stage complete --workitem-file /tmp/live-task.json
```

All gates are read-only. `ready=false` exits 2; inspect the JSON blockers and limitations, rather than treating a successful process invocation as authorization.

- implement: sufficient brief and current design decision.
- review: current self_review and required review criteria; dirty/uncommitted changes are not covered by HEAD evidence.
- merge: review checks, exact-head merge authorization, live bound non-Draft OPEN PR, a known live base integrated in the checked head, and passed required GitHub checks. Use `sync-task` in the task directory for base updates/conflict resolution, then reverify and update the existing PR. Inspect mergeability and original authorization before merging with an exact-head guard. Ready is eligibility, not consent.
- complete: all required criteria, scoped human acceptance when required by existing policy/label, live merged primary PR, fresh Plane task/labels, confirmed delivery writeback and resource cleanup/handoff. Actual PR head controls evidence even after a squash merge changes local main's SHA. Verify merged content separately. The gate neither merges nor writes Plane state.

For completion, read the live task through MCP and save this normalized snapshot outside the tracked worktree immediately before checking:

```json
{
  "task": "PROJECT-123",
  "project_id": "actual-mapped-project-uuid",
  "labels": ["actual-current-label-names"],
  "state_group": "actual-current-group",
  "observed_at": "timezone-aware-time-of-the-MCP-read"
}
```

Only snapshots within five minutes and for the mapped task/project are accepted. Actual manual labels override on_merge as before. Missing evidence leaves completion blocked; do not replay cached reads. Completed/cancelled work is preserved by the existing execution rules. Native/basic modes still have no plugin-owned automatic completion target.

## Delivery report and partial success

```sh
python3 /absolute/plugin/scripts/plane_workflow.py render-report PROJECT-123 --repo /absolute/task-directory --summary-file /tmp/summary.md --from-progress --output /tmp/report.md
python3 /absolute/plugin/scripts/plane_workflow.py deliver PROJECT-123 --repo /absolute/task-directory --title "Resulting behavior" --body-file /tmp/report.md --apply
```

Summary describes resulting behavior, not historical PR status. The structured renderer derives checks/staleness, accepted criterion scope, blockers, limitations and environment from current data; original human quotes and history stay private. At completion use `--stage complete --workitem-file /tmp/live-task.json` to include newly observed PR facts. Regenerate the current Plane delivery report rather than appending obsolete status paragraphs. The agent writes implementation/acceptance reports; Actions writes separate lifecycle facts. Custom state rules and background acceptance inference are not added.

Incomplete work can use `deliver --draft`; its blockers remain visible and the Skill preserves the current task state rather than moving it into review. Updating a review PR with incomplete work converts it to Draft. A ready gate does not silently promote an existing Draft. Explicitly run gh pr ready only within authorized review scope after rechecking its head and the review gate. Existing legacy free-text render-report inputs remain available for compatibility; regular delivery still checks the receipt, and the Skill uses structured rendering.

Record delivery writeback as pending until MCP link/comment operations have been read back. On partial success inspect actual GitHub/Plane state and resume only the missing operation; retain the branch/PR, reuse links and stable comments. Task recording alone sends nothing to Plane/GitHub. Installing the plugin does not update copied synchronization scripts in business repositories.
