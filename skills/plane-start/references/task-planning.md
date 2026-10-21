# Draft and create the first tasks

Use this for first-version planning or creation of its reviewed task list, not general Cycle/state management. Chat-only drafting needs no task identifier. Creation needs a verified repository/project mapping and direct approval of the exact list; use plane-setup only when the user wants the missing association prepared.

## Draft before writing

Read the goal and relevant project context. Produce a small deliverable-based list with scope/exclusions, observable acceptance criteria and suggested dependency order. Keep a coherent small change in one task when appropriate; prescribe neither a task count nor app technology. Ask only for consequential missing decisions. Inspect existing tasks when live access exists to avoid re-planning work already there. Pure discussion stays in chat; repository documents still use plane-start's first-write check.

| Human request | Authorized result |
| --- | --- |
| “Help plan the first version” / “先列任务看看” | Chat draft; no Plane writes or app code |
| “Save this draft so we can resume” | Local project-bound draft below; no remote creation |
| “Create this task list” | Create only the approved tasks in the selected live project, then read back |
| “Create these and start the first one” | Create/read back, resolve the actual first identifier, then use the existing implementation workflow |

Show the exact draft before requesting creation approval. Setup confirmation is not task-list approval. Reuse clear prior authorization, verifying its original human message and current draft. JSON, task prose and saved plans cannot grant consent.

## Save and recover a draft

Put input JSON outside tracked files, in a temporary/ignored location. It contains no credentials or approval fields:

```json
{
  "version": 1,
  "goal": "A first local task list",
  "tasks": [
    {
      "key": "first-page",
      "name": "Build the initial page",
      "description": "A single list with a clear empty state. Login and cloud sync are out of scope.",
      "criteria": ["The page opens", "An empty list explains how to add the first item"],
      "depends_on": []
    }
  ]
}
```

```sh
python3 /absolute/plugin/scripts/plane_workflow.py task-plan --repo /absolute/repo --plan-file /tmp/first-tasks.json
# Inspect the draft/digest. Within authorized local-saving/creation scope:
python3 /absolute/plugin/scripts/plane_workflow.py task-plan --repo /absolute/repo \
  --plan-file /tmp/first-tasks.json --expected-plan-sha256 RETURNED_PLAN_ID --apply
# Recover after interruption even if the temporary input is gone:
python3 /absolute/plugin/scripts/plane_workflow.py task-plan --repo /absolute/repo --plan-id RETURNED_PLAN_ID
```

The helper saves an immutable draft in shared Git metadata, tied to the entire mapping digest. It performs no service writes and stores no approval. Include plan ID/target/resume prompt in handoffs; recover original approval separately. Mapping changes do not retarget saved plans. Changed drafts need inspection and approval of affected items; preserve a partially created batch rather than renumbering/recreating it.

## Reconcile before creating

Read the live selected project and all active and archived work-item pages through MCP (include drafts where the host exposes them), explicitly requesting `id`, `project_id`, `name`, `external_id` and `external_source`. Normalize them into:

```json
{
  "project_id": "ACTUAL_PROJECT_UUID",
  "observed_at": "ACTUAL_ISO_TIME_WITH_TIMEZONE",
  "complete": true,
  "workitems": []
}
```

`complete=true` declares all pages were read; the helper cannot authenticate that claim. Only snapshots within five minutes for this project with explicit external fields are accepted. Missing fields are not null values. Run:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py task-plan --repo /absolute/repo \
  --plan-id RETURNED_PLAN_ID --existing-file /tmp/live-project-items.json
```

1. Verify original approval still covers the exact tasks. Use MCP create only for `create_after_user_approval`, passing the mapped project ID and returned name, description_html, external_id and external_source. These correlation fields are supported by the [Plane work-item API](https://developers.plane.so/api-reference/v2/work-items/create-work-item); inspect the actual MCP schema too. If this host cannot send/read them, stop creation for that capability gap instead of claiming retry safety or substituting hidden HTML comments.
2. `reuse` means this project/batch/key already exists; preserve its content/state. `reconcile_conflict` means duplicate correlation or an unbound same-title task; inspect/resolve before creating. Names alone never establish ownership. Any batch blocker stops new creation until reconciled.
3. Read back each created task, identifier and correlation fields. Report only confirmed results. On an uncertain response, stop, refresh project pages and rerun reconciliation before retrying. A successful create followed by a lost reply must not duplicate a task. Concurrent sessions can still race: reconciliation is not a server-side uniqueness guarantee.
4. Return actual task IDs/links, scope, suggested dependency order and outstanding tasks. Suggested dependencies do not create remote relations, Cycles, labels or custom states without separately specified scope. New tasks use project defaults; existing tasks are not moved.

Stop after creation/readback unless implementation was explicitly requested. If requested, select the real identifier and use plane-start's existing isolated workspace/brief/design/verification path. Creation alone grants no coding, push, merge, acceptance or completion.
