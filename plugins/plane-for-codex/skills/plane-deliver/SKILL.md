---
name: plane-deliver
description: Deliver a Plane task as a linked GitHub pull request and write back implementation and verification results, or finalize a task after explicit acceptance.
---

# Deliver a Plane task

Resolve `../../scripts/plane_workflow.py` relative to this SKILL.md's directory and invoke it using its absolute path. Read [the workflow reference](../../references/workflow.md) for report and PR commands.

When selected without additional prose, resolve the current task from repository mapping plus its task branch, bound PR or unambiguous user context. Ask for task selection only if those disagree or identify no single task. Explicitly selecting this delivery Skill requests the normal commit/push/PR and Plane writeback workflow; preserve any narrower user constraints and completion/acceptance requirements.

1. Load the repository mapping and task through MCP. Inspect the actual diff, branch and required checks. Include only the task's intended files in commits; preserve other work.
2. Write a report with the implemented change, observed verification results, remaining acceptance steps, and any limitations. Use `render-report` to create a reusable PR body with a primary `[PROJECT-123]` reference and a machine-readable binding. Never put credentials or internal reasoning in this report.
3. Within the user's authorized delivery scope, commit, push and create or update the PR against the configured base branch. Reuse the existing task PR on retries. If delivery authorization excludes an external operation, prepare its concrete result before requesting the missing authorization. Attach newly created PRs with the host attachment tool when available.
4. Through MCP, add PR URL and a delivery comment with stable `plane-for-codex:<repository>:<PR number>:delivery` marker; update a matching comment instead of duplicating it. Include implementation, checks and remaining acceptance. Move to `in_review` only with Actions provider and legacy config version 1 state synchronization enabled and when not completed/canceled. Basic version 2 preserves state while writing the report. If Plane fails after GitHub succeeds, retain the PR and retry only Plane writeback.
5. In Actions mode, completion follows the configured policy. In native mode, inspect and explain the official rules; local settings cannot enforce native transitions. Do not automatically move review/completion states through MCP alongside the official integration. `on_merge` permits Done after the primary PR has actually merged into the configured branch; `manual` requires the user's explicit acceptance as well. A `manual-acceptance` Plane label always requires acceptance. Submission, tests and visual/device acceptance are separate facts. Closing an unmerged PR leaves work unfinished.

When the user accepts and authorizes finalization, verify checks and PR state, perform authorized merge and record evidence. Write the configured completion state only with Actions provider and legacy synchronization enabled. In native mode, an explicit user-requested state change is separate from automatic PR synchronization; resolve the actual state and preserve acceptance requirements. Basic version 2 has no automatic target: report acceptance without changing state; explicit state requests use the project's actual states. Legacy Actions handle lifecycle writeback when enabled. One primary task PR per work item remains the completion contract.
