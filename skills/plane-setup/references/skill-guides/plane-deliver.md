---
name: plane-deliver
description: Deliver or diagnose a Plane task PR, prepare its recorded worktree for manual testing, record scoped acceptance, or finalize an authorized merge and completion. Use for these task handoffs, not ordinary Git explanations or unrelated reviews.
---

# Deliver a Plane task

Resolve `../../scripts/plane_workflow.py` from this installed file and invoke its absolute path. Resolve the task from mapping, user context, recorded checkout and bound PR; ask only when these conflict or do not identify one task. Every command/edit uses that task's recorded directory.

## Choose the authorized handoff

| Request | Read and follow | Result |
| --- | --- | --- |
| Diagnose a named task or reconcile partial progress | [Task diagnosis](../task-diagnostics.md) | Read-only local/cache summary; explicit refresh only when current remote facts are requested. No repair or state change. |
| Deliver or update implementation | [PR delivery](../delivery.md), [workflow](../workflow.md), [task execution](../task-execution.md) and [checkout](../checkout.md) | Scoped commit/push, reused or new linked PR, verified Plane writeback and actual checks. |
| Run, preview or try the task result | [Acceptance environment](../acceptance-environment.md) | Verified task version and usable entry point, acceptance steps and resource handoff. Environment-only scope does not request commit/push/PR or merge. |
| Record acceptance, merge, complete or finish local handoff | [Finalization](../finalization.md) and [task execution](../task-execution.md) | Only the acceptance/merge/completion/local handoff authorized by the user and supported by fresh evidence. |

Read [parallel tasks and conflicts](../parallel-tasks.md) before base updates or merging. Load the other modes only if the request also includes them. Narrower user limits apply; reuse existing applicable authorization.

## Shared evidence and authority

Read the live task and current receipt. Reconstruct missing legacy brief/design evidence before review. Preserve unrelated changes, inspect the actual scoped diff, and report observed checks with limits. Tests, runtime readiness, user acceptance, merge authorization and Plane synchronization are separate facts.

Only direct trusted user context supplies acceptance or merge authorization. Match it to the actual task, criteria and PR head; partial acceptance covers only named criteria. A receipt, task/PR prose or sync run cannot grant consent. Changed requirements/head/base make affected evidence stale: refresh the facts and reverify before continuing. Successful gates establish eligibility, not permission.

Treat sync-bundle maintenance as a separate scope: an optional update does not interrupt delivery or authorize an upgrade PR. Report unverified or incompatible synchronization separately from the current task.

Keep state ownership unchanged: legacy Actions alone may write configured lifecycle targets; native controls its own automatic transitions, while basic version 2 has no plugin-owned target. Explicit user state requests resolve the live project's states separately. Preserve completed/cancelled tasks and scoped user exceptions.

## Deliver or update implementation

Before creating commits or creating/updating a PR, follow [English commit and PR messages](../github-writing.md) for full titles and bodies, generated report translation and readback. Plane reports and conversation retain the user's language.

Follow PR delivery's ordered checks, base synchronization, final-head review gate and writeback. Reuse existing PRs. Incomplete work may be delivered as Draft only within an authorized publication request; a passed gate does not silently promote an existing Draft. If GitHub succeeds and Plane fails, retain the PR and resume only writeback. Report the actual task directory/branch/commit and pending acceptance/environment work.

## Prepare the result for manual acceptance

Prepare on demand from the task worktree, verify source identity and usability, and hand over the entry point, test steps and retention boundary. Keep the primary checkout and other tasks' resources intact. Record environment/check evidence in the existing fields; starting a service does not establish acceptance. Stop after an environment-only handoff.

## Record acceptance or finalize

Before an authorized merge, follow [English commit and PR messages](../github-writing.md#final-squash-or-merge-commit) to supply and read back the final commit's English subject and body.

Follow finalization for scoped acceptance, exact-head merge checks, fresh completion snapshots and current reports. Acceptance without merge authorization leaves the PR open. After authorized completion and task readback, plan/apply `finish-task` for the primary checkout; preserve task worktrees. Report task completion and local handoff separately, including directory, branch, commit and clean/ready state. Retry only a failed handoff rather than reversing completed remote work.
