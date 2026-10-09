---
name: plane-start
description: Start development on an existing Plane work item by its task identifier or link, with a linked Git branch or isolated worktree.
---

# Start a Plane task

Resolve `../../scripts/plane_workflow.py` relative to this SKILL.md's directory and invoke it using its absolute path. Read [the workflow reference](../../references/workflow.md) for branch preparation and reporting commands.

1. Load `.plane-for-codex.json` from the target Git repository and run `doctor`. Use `plane-setup` if it is missing.
2. Parse the task identifier or Plane link supplied by the user. Through Plane MCP, retrieve the work item, its complete description, comments, and relevant sub-items/relations. Confirm workspace, project and acceptance scope against the repo mapping. Summarize the intended change; clarify only missing information that affects implementation. Never silently develop a task in another project.
3. Inspect the current branch, worktree and uncommitted changes. Fetch the configured origin base branch before creating a new task branch. Ensure setup mapping is committed in that base branch. Run `prepare` to inspect a branch plan. Apply it when the user has authorized starting development. If unrelated changes require isolation, use `--worktree` and work in the returned directory. Existing task branches can be resumed; preserve their changes.
4. After the branch is ready, update the work item to the configured `in_progress` state through MCP. Preserve completed/canceled work unless the user explicitly reopens it. If the write fails, report it and keep the prepared branch; retry the sync rather than recreating the branch.
5. Implement the task using the repository's conventions and appropriate verification. Store evolving decisions in the task only when relevant and authorized; avoid publishing every internal update.
6. When ready to deliver, follow `plane-deliver`. Report blockers and incomplete acceptance clearly instead of marking them done.

A successful start proves that the chosen work item belongs to the mapped project, its requirements have been read, and development is happening on the returned branch/worktree. Creating a branch alone does not prove the task has been implemented.
