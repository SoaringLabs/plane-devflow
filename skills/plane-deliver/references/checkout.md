# Task checkout and completion handoff

Read this before saving any task artifact in the repository, during task preparation, every resumed write turn, before committing/delivering, and after confirmed task completion. The configured base is used throughout; it is usually `main`. These checks leave existing acceptance/merge authorization unchanged.

## Before the first repository write

Plans, research notes, designs and tests are repository changes just like application code, including new untracked or ignored files. Resolve task ownership before their first write; a new chat or the currently checked-out branch is insufficient evidence of a new/resumed task. When the request is discussion or analysis only, return the answer in chat. Use temporary storage outside the checkout if needed, including for another skill's default Markdown output. A request for a saved artifact authorizes that artifact, not implementation, Plane state changes, merge or publication.

`write-context` is a read-only preflight. It does not select a task from the current branch, create files/metadata, fetch, switch branches or start a task. Discussion succeeds without task selection but grants no repository writes. Write mode requires an explicitly resolved task, an existing checkout binding, authorized file scope, and concrete planned paths; it checks both accumulated changes and files that do not exist yet. A failing check exits 2 and supplies blockers/next action. Success describes current state, not durable authorization or a filesystem interceptor; rerun immediately before edits and review semantic ownership within permitted files.

Save authored task artifacts at trackable paths. Planned Git-ignored artifacts are blocked even when already present: Git branch/scope history cannot establish their ownership across switches. Use external temporary storage or a trackable document path instead. Planned paths also reject symlinks in the file or parent directories; use the actual scoped target to keep path ownership meaningful. These checks examine only requested artifact paths; they do not inventory dependencies/build caches or change existing ignore rules.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py write-context \
  --repo /absolute/application/repo --mode discussion
python3 /absolute/plugin/scripts/plane_workflow.py write-context PROJECT-123 \
  --repo /absolute/task-directory --mode write \
  --path docs/research/requirement.md --path docs/plans/implementation.md
```

If the task is unknown, continue discussion outside the checkout and resolve only the missing identity before saving. For a new task, plan/apply `prepare` to allocate an independent worktree and fetch the configured origin base, use its returned execution directory, record scope through `task-context`, then rerun the write preflight. See [parallel tasks](parallel-tasks.md) for native worktree attachments and PR conflict resolution. New task branches derive from that base rather than the previous task's HEAD; there is no required intermediate switch to local `main`. If a branch/context already exists, inspect and resume it. Dirty or differently owned checkouts retain all files and branches; use the existing isolation/recovery rules rather than moving documents or stashing automatically. Fetch failures leave base freshness unverified and must be resolved or explicitly accepted before new-branch writes.

For a requested planning document, the checkout/scope/write checks are sufficient; implementation brief/design gates apply before coding. Existing task-state transitions remain limited to authorized implementation. Pass the selected task, directory, allowed paths and discussion/write mode to any delegated work or other skill so its output stays in the same scope.

## Bind and check development

`prepare --apply` records the selected task directory, branch and original base commit under shared Git metadata. Resume preserves this baseline and file scope. Before new preparation or resumed work, fetch the configured base using `git fetch origin BASE`; a failed fetch leaves remote freshness unverified. A branch-only request can stop after preparation with file scope still pending.

Before the first repository write, derive an explicit list of repository-relative paths/glob patterns from the agreed task scope and inspected code, including planned artifacts and relevant tests. Save the JSON array outside the tracked checkout. Broad patterns need a real broad requirement; generating a scope from all observed changed files would silently adopt unrelated work. This is an agent implementation choice within authorized scope, not another human approval step.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py task-context PROJECT-123 --repo /absolute/task-directory
python3 /absolute/plugin/scripts/plane_workflow.py task-context PROJECT-123 \
  --repo /absolute/task-directory --scope-file /tmp/task-paths.json
python3 /absolute/plugin/scripts/plane_workflow.py task-context PROJECT-123 \
  --repo /absolute/task-directory --scope-file /tmp/task-paths.json \
  --expected-context-sha256 INSPECTED_DIGEST --apply
python3 /absolute/plugin/scripts/plane_workflow.py check-task PROJECT-123 \
  --repo /absolute/task-directory --stage implement
```

Example scope: `["src/components/date-picker.tsx", "src/modules/calendar/**", "tests/date-picker*.test.ts"]`. Patterns match the complete repository-relative path, including nested directories. Renames check both source and destination. The recorded starting base remains immutable; checks account for the current task difference from its merge base with the configured base, plus staged, unstaged and untracked files. During a recognized base merge, clean incoming base files are excluded, while task edits and conflict resolutions remain scoped. This allows another task's merged files to enter through the base without expanding the task's authorized paths. They also reject branch/directory drift, rewritten base history and a task head already contained in the known base. Implement/review/merge gates enforce this check; Draft delivery cannot bypass it. Human/agent diff review still determines whether changes inside an allowed file belong to the task.

On each resumed development turn and immediately before edits/commits, run `task-context`; before delivery refresh the base and check again. Resolve blockers before continuing. Branch changes and unexpected files require inspecting ownership, not adopting them into scope or automatically moving them. Already integrated code must be reconciled with its real merge/commit and Plane association; do not manufacture a duplicate PR. A known legitimate history rewrite or directory migration requires inspecting the original context and explicit recovery; the helper preserves the old record rather than resetting it automatically.

Legacy tasks have no checkout record. Reconstruct from the original task branch, live PR and accessible conversation, then plan/apply `task-context --scope-file` in the verified directory. Its baseline is the merge base with the known configured base, and it cannot prove previously unrecorded branch continuity. Inspect the full difference before accepting this reconstruction. Record hashes authenticate no user decision.

## Finish and prepare the next task

After authorized task finalization, finish the Plane report/link writeback and read back the actual completed task and merged PR. Immediately save a fresh normalized completed snapshot as described in task execution. The normal Deliver flow then plans/applies the following without another confirmation, unless the user's instruction explicitly excludes local checkout updates:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py finish-task PROJECT-123 \
  --repo /absolute/task-directory --workitem-file /tmp/completed-task.json
python3 /absolute/plugin/scripts/plane_workflow.py finish-task PROJECT-123 \
  --repo /absolute/task-directory --workitem-file /tmp/completed-task.json --apply
```

Each call checks fresh completion evidence; a plan or saved checkpoint is not current proof or remote-operation authorization. The helper does no Plane writes, merges, branch deletion or worktree removal. It updates the primary checkout, preserving a separate task worktree. The primary and caller checkout must be clean, on the base or this task branch, and free of ongoing Git operations. If the base is held by a different worktree, leave it intact and report its ownership conflict.

Apply fetches the configured origin base, verifies that it contains the actual PR merge commit, and requires local base history to be an ancestor of the refreshed base. Local unique/divergent commits stop the operation before switching. Then it switches to the base (or creates its missing tracking branch), explicitly pulls that origin branch with `--ff-only`, and verifies a clean checkout, base branch, local/remote equality and inclusion of the merge commit. A newer base commit is valid; it need not equal this task's merge commit.

The result reports `path`, `base`, `head`, `remote_head`, `merge_commit`, phase and ready/pending status. Saved local handoff checkpoints live separately from completion receipts in shared Git metadata. Failures preserve completed Plane state and all existing work. Re-read current task/PR facts and rerun only `finish-task`; it resumes from the actual current checkout, including a prior successful switch followed by a failed pull. Report “task complete; local handoff pending” until verification succeeds.

Final user output includes the prepared directory, branch and commit, whether the checkout is clean, and whether the next task can start. If the chat is attached to a preserved task worktree, identify the primary directory explicitly; updating its files does not move the current agent session to another directory. The next task must still refresh the base before creating its own branch.
