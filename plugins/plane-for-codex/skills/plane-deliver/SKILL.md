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
4. Through MCP, add the PR URL and a delivery comment carrying a stable `plane-for-codex:<repository>:<PR number>:delivery` marker. Search existing comments and update the matching comment instead of posting duplicates. Include the implementation, checks and remaining acceptance in the comment. Move the task to `in_review` unless it is already completed/canceled. If GitHub succeeds but Plane fails, preserve and report the PR, then retry only the Plane writeback.
5. Completion follows the configured policy. `on_merge` permits Done after the primary PR has actually merged into the configured branch; `manual` requires the user's explicit acceptance as well. A `manual-acceptance` Plane label always requires acceptance. Submission, tests and visual/device acceptance are separate facts. Closing an unmerged PR leaves work unfinished.

When the user explicitly accepts and authorizes finalization, verify outstanding checks and PR state, perform any authorized merge, then update Plane to Done and record the evidence. With Actions enabled, GitHub events perform PR lifecycle writeback; the agent still supplies the development report. Without Actions, verify the actual PR state through GitHub and do the writeback through MCP. One primary task PR per work item is the v1 completion contract; split or discuss multi-PR delivery before using automatic completion.
