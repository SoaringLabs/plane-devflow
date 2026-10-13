# Task checkout and completion handoff

Read this during task preparation, every resumed development turn, before committing/delivering, and after confirmed task completion. The configured base is used throughout; it is usually `main`. These checks leave existing state rules and acceptance/merge authorization unchanged.

## Bind and check development

`prepare --apply` records the selected task directory, branch and original base commit under shared Git metadata. Resume preserves this baseline and file scope. Before new preparation or resumed work, fetch the configured base using `git fetch origin BASE`; a failed fetch leaves remote freshness unverified. A branch-only request can stop after preparation with file scope still pending.

Before coding, derive an explicit list of repository-relative paths/glob patterns from the agreed task scope and inspected code, including relevant tests. Save the JSON array outside the tracked checkout. Broad patterns need a real broad requirement; generating a scope from all observed changed files would silently adopt unrelated work. This is an agent implementation choice within authorized scope, not another human approval step.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py task-context PROJECT-123 --repo /absolute/application/repo
python3 /absolute/plugin/scripts/plane_workflow.py task-context PROJECT-123 \
  --repo /absolute/application/repo --scope-file /tmp/task-paths.json
python3 /absolute/plugin/scripts/plane_workflow.py task-context PROJECT-123 \
  --repo /absolute/application/repo --scope-file /tmp/task-paths.json \
  --expected-context-sha256 INSPECTED_DIGEST --apply
python3 /absolute/plugin/scripts/plane_workflow.py check-task PROJECT-123 \
  --repo /absolute/application/repo --stage implement
```

Example scope: `["src/components/date-picker.tsx", "src/modules/calendar/**", "tests/date-picker*.test.ts"]`. Patterns match the complete repository-relative path, including nested directories. Renames check both source and destination. Checks account for cumulative committed differences from the recorded base plus staged, unstaged and untracked files. They also reject branch/directory drift, rewritten base history and a task head already contained in the known base. Implement/review/merge gates enforce this check; Draft delivery cannot bypass it. Human/agent diff review still determines whether changes inside an allowed file belong to the task.

On each resumed development turn and immediately before edits/commits, run `task-context`; before delivery refresh the base and check again. Resolve blockers before continuing. Branch changes and unexpected files require inspecting ownership, not adopting them into scope or automatically moving them. Already integrated code must be reconciled with its real merge/commit and Plane association; do not manufacture a duplicate PR. A known legitimate history rewrite or directory migration requires inspecting the original context and explicit recovery; the helper preserves the old record rather than resetting it automatically.

Legacy tasks have no checkout record. Reconstruct from the original task branch, live PR and accessible conversation, then plan/apply `task-context --scope-file` in the verified directory. Its baseline is the merge base with the known configured base, and it cannot prove previously unrecorded branch continuity. Inspect the full difference before accepting this reconstruction. Record hashes authenticate no user decision.

## Finish and prepare the next task

After authorized task finalization, finish the Plane report/link writeback and read back the actual completed task and merged PR. Immediately save a fresh normalized completed snapshot as described in task execution. The normal Deliver flow then plans/applies the following without another confirmation, unless the user's instruction explicitly excludes local checkout updates:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py finish-task PROJECT-123 \
  --repo /absolute/application/repo --workitem-file /tmp/completed-task.json
python3 /absolute/plugin/scripts/plane_workflow.py finish-task PROJECT-123 \
  --repo /absolute/application/repo --workitem-file /tmp/completed-task.json --apply
```

Each call checks fresh completion evidence; a plan or saved checkpoint is not current proof or remote-operation authorization. The helper does no Plane writes, merges, branch deletion or worktree removal. It updates the primary checkout, preserving a separate task worktree. The primary and caller checkout must be clean, on the base or this task branch, and free of ongoing Git operations. If the base is held by a different worktree, leave it intact and report its ownership conflict.

Apply fetches the configured origin base, verifies that it contains the actual PR merge commit, and requires local base history to be an ancestor of the refreshed base. Local unique/divergent commits stop the operation before switching. Then it switches to the base (or creates its missing tracking branch), explicitly pulls that origin branch with `--ff-only`, and verifies a clean checkout, base branch, local/remote equality and inclusion of the merge commit. A newer base commit is valid; it need not equal this task's merge commit.

The result reports `path`, `base`, `head`, `remote_head`, `merge_commit`, phase and ready/pending status. Saved local handoff checkpoints live separately from completion receipts in shared Git metadata. Failures preserve completed Plane state and all existing work. Re-read current task/PR facts and rerun only `finish-task`; it resumes from the actual current checkout, including a prior successful switch followed by a failed pull. Report “task complete; local handoff pending” until verification succeeds.

Final user output includes the prepared directory, branch and commit, whether the checkout is clean, and whether the next task can start. If the chat is attached to a preserved task worktree, identify the primary directory explicitly; updating its files does not move the current Codex chat to another directory. The next task must still refresh the base before creating its own branch.
