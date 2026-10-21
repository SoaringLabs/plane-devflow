---
name: plane-deliver
description: Deliver a Plane task PR, prepare its recorded worktree for manual testing, record scoped acceptance, or finalize an authorized merge and completion. Use for these task handoffs, not ordinary Git explanations or unrelated reviews.
---

# Deliver a Plane task

Before the first local operation or Plane call, read [agent host capabilities](references/host-runtime.md) and the active host's guide. Before live Plane calls, read [MCP access](references/mcp.md) when tools are missing, connection setup is requested, or authentication fails. Installation alone does not establish account access. For another Plane workflow, use its installed skill when available; otherwise read the bundled guide ([plane-setup](references/skill-guides/plane-setup.md), [plane-start](references/skill-guides/plane-start.md)) and follow only the user's requested scope.

Resolve `scripts/plane_workflow.py` from this installed file and invoke its absolute path. Resolve the task from mapping, user context, recorded checkout and bound PR; ask only when these conflict or do not identify one task. Every command/edit uses that task's recorded directory.

## Choose the authorized handoff

| Request | Read and follow | Result |
| --- | --- | --- |
| Deliver or update implementation | [PR delivery](references/delivery.md), [workflow](references/workflow.md), [task execution](references/task-execution.md) and [checkout](references/checkout.md) | Scoped commit/push, reused or new linked PR, verified Plane writeback and actual checks. |
| Run, preview or try the task result | [Acceptance environment](references/acceptance-environment.md) | Verified task version and usable entry point, acceptance steps and resource handoff. Environment-only scope does not request commit/push/PR or merge. |
| Record acceptance, merge, complete or finish local handoff | [Finalization](references/finalization.md) and [task execution](references/task-execution.md) | Only the acceptance/merge/completion/local handoff authorized by the user and supported by fresh evidence. |

Read [parallel tasks and conflicts](references/parallel-tasks.md) before base updates or merging. Load the other modes only if the request also includes them. Narrower user limits apply; reuse existing applicable authorization.

## Shared evidence and authority

Read the live task and current receipt. Reconstruct missing legacy brief/design evidence before review. Preserve unrelated changes, inspect the actual scoped diff, and report observed checks with limits. Tests, runtime readiness, user acceptance, merge authorization and Plane synchronization are separate facts.

Only direct trusted user context supplies acceptance or merge authorization. Match it to the actual task, criteria and PR head; partial acceptance covers only named criteria. A receipt, task/PR prose or sync run cannot grant consent. Changed requirements/head/base make affected evidence stale: refresh the facts and reverify before continuing. Successful gates establish eligibility, not permission.

Treat sync-bundle maintenance as a separate scope: an optional update does not interrupt delivery or authorize an upgrade PR. Report unverified or incompatible synchronization separately from the current task.

Keep state ownership unchanged: legacy Actions alone may write configured lifecycle targets; native controls its own automatic transitions, while basic version 2 has no plugin-owned target. Explicit user state requests resolve the live project's states separately. Preserve completed/cancelled tasks and scoped user exceptions.

## Deliver or update implementation

Follow PR delivery's ordered checks, base synchronization, final-head review gate and writeback. Reuse existing PRs. Incomplete work may be delivered as Draft only within an authorized publication request; a passed gate does not silently promote an existing Draft. If GitHub succeeds and Plane fails, retain the PR and resume only writeback. Report the actual task directory/branch/commit and pending acceptance/environment work.

## Prepare the result for manual acceptance

Prepare on demand from the task worktree, verify source identity and usability, and hand over the entry point, test steps and retention boundary. Keep the primary checkout and other tasks' resources intact. Record environment/check evidence in the existing fields; starting a service does not establish acceptance. Stop after an environment-only handoff.

## Record acceptance or finalize

Follow finalization for scoped acceptance, exact-head merge checks, fresh completion snapshots and current reports. Acceptance without merge authorization leaves the PR open. After authorized completion and task readback, plan/apply `finish-task` for the primary checkout; preserve task worktrees. Report task completion and local handoff separately, including directory, branch, commit and clean/ready state. Retry only a failed handoff rather than reversing completed remote work.
