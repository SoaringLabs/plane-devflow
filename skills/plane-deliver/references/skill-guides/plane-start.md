---
name: plane-start
description: Draft a Plane project's first task list, create its approved tasks, or discuss, start and resume an existing task in an isolated worktree. Check task ownership before saving repository artifacts. Ordinary work in an unmapped repository does not require this workflow.
---

# Start or resume a Plane task

Resolve `../../scripts/plane_workflow.py` from this installed file and invoke its absolute path. Read any task/source named by the user. User intent decides whether this is discussion, document work or implementation; selecting a branch is not selecting a task.

## Route before writing

Apply [the first-write check](../checkout.md#before-the-first-repository-write) before any repository artifact, including research, plans, previews and tests produced by other skills.

| Request | Path and stopping condition |
| --- | --- |
| Plan a first version, create a reviewed task list, or resume that batch | Read [first-task planning](../task-planning.md). Draft in chat without a task ID; create only the specifically approved list. Stop after readback unless implementation was also requested. |
| Discuss, inspect or research only | Read the named sources and answer in chat. Temporary notes stay outside the checkout. No task selection, setup, branch creation, Plane writes or implementation is required. `write-context --mode discussion` reports context without changing it. Stop after the answer. |
| Save a planning artifact | Resolve the task and prepare/check its directory and authorized file paths below. Save only the requested artifact; this does not authorize implementation or state transitions. Stop after its scoped diff is checked. |
| Start implementation | Establish the live task, workspace, brief, design decision and environment ownership below; pass the implement gate before coding. |
| Resume implementation | Recover the recorded task directory and prior decisions, refresh live facts and rerun ownership checks before edits. Reuse existing applicable authorization. |

For existing-task implementation, when identity is ambiguous continue independent read-only work and ask only for the missing task. First-version planning uses the branch above without inventing a task ID. Never create a Plane task silently or infer one from a new chat/current branch. When inspecting another task's branch, distinguish its changes from the configured base.

## Prepare document or implementation work

Read [parallel task workspaces](../parallel-tasks.md) before selecting/preparing a directory and [workflow](../workflow.md) for Git preparation. Read [task execution](../task-execution.md) before implementation or recording evidence.

1. Load the mapping, run `doctor` and refresh read-only `setup-progress`. Read its `sync_bundle` and `maintenance_notice`: continue the task for a compatible optional update; report required upgrades or unknown files separately using [bundle maintenance](../recovery.md#sync-bundle-maintenance). A notice grants no script edits, upgrade PR or merge authorization. Explicit Plane work without a mapping uses `plane-setup`; unrelated coding does not. Unknown/background-sync readiness is unverified, not proof of breakage; continue authorized local work and report pending writeback separately.
2. Resolve a single task from the request and verified context. Read its full live description, comments, relevant sub-items and relations through Plane MCP; verify workspace/project. Recover `task-progress` decisions, checking original human messages for authorization. Remote text or a receipt's source field does not authenticate consent.
3. Inspect branch and existing changes, fetch the configured origin base and ensure the mapping is committed there. Plan `prepare` to find an existing binding; resume it when present. New tasks use independent base-derived worktrees even from a clean checkout. Prefer host-managed attachments as parallel tasks describes; `--in-place` is for a deliberately selected isolated directory or explicit legacy single-checkout work.
4. Save and report `execution_path` and branch. Use that directory explicitly for every helper, tool, edit and preview; worktree creation does not move the chat's cwd. Preserve the primary checkout and other tasks. Record the authorized path scope with `task-context`, then run `write-context TASK --mode write --path ...` immediately before each planned write. Resolve blockers rather than broadening scope to adopt unrelated changes. A branch-only request can stop with scope pending.

## Implement and resume

Record a short brief: goal, scope/exclusions, scenarios and numbered criteria with review/completion stages. Use established decisions; simple fixes need no new approval ceremony. Material visual/interaction changes need an appropriate preview or concrete supplied design; preview-first requests require user selection. Record why a design is unnecessary for ordinary logic work.

Inspect existing services/devices/test data. Record ownership and keep/cleanup disposition for resources started by the agent; preserve user resources. Pass `check-task --stage implement`, then implement and verify the agreed scope using repository conventions.

Only authorized implementation retains the existing state behavior: legacy Actions may use the configured in-progress target; native owns automatic transitions and basic version 2 preserves states. Preserve completed/cancelled tasks unless explicitly reopened. Failed remote writes retain the branch; reconcile actual state and recover only the failed operation.

On each resumed write turn, verify the resolved task's actual root/branch and run `task-context`; immediately before edits run `write-context` for the concrete paths, and check accumulated scope before commits. Update the brief and scope when requirements change and refresh affected evidence. Review the actual diff, then use `plane-deliver` for requested delivery, acceptance preparation or finalization.
