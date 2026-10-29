# Parallel tasks in one project

Different chats in one Codex project can develop different Plane tasks concurrently. Each new task uses an independent worktree and task branch from the freshly fetched configured base (normally `main`); each task delivers its own primary PR back to that base. Existing acceptance, merge authorization and Plane state ownership still apply.

## Prepare and use the right directory

For a selected task, plan/apply `prepare` without `--in-place`. Its default creates an isolated directory beside the primary checkout, or resumes the task's recorded directory/branch. It never switches the primary checkout or another task's checkout, even when those directories are clean. Apply fetches the configured origin base before preparing the branch. Preparation is serialized briefly in shared Git metadata; development in separate directories remains independent. Preserve a busy/stale lock for inspection rather than deleting it automatically.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py prepare PROJECT-123 --repo /absolute/project --agent HOST
python3 /absolute/plugin/scripts/plane_workflow.py prepare PROJECT-123 --repo /absolute/project --agent HOST --apply
```

The result supplies `execution_path`, `branch`, `primary_path`, the fetched `base_sha` and `execution.current.id` on apply. New tasks start at that base, rather than the caller's feature HEAD or uncommitted changes. Existing tasks preserve the original baseline and authorized scope. A missing or differently owned bound checkout needs explicit recovery; it is not silently replaced. `--worktree PATH` selects an explicit isolated location and follows the same freshness/ownership checks.

## Agent naming and serial continuation

Pass the actual session's host as `HOST`, independently of installed CLIs or the skill installation target:

| Host | `--agent` | New-task default prefix |
| --- | --- | --- |
| Codex | `codex` | `codex` |
| Claude Code | `claude-code` | `claude` |
| Cursor | `cursor` | `cursor` |
| OpenCode | `opencode` | `opencode` |

An omitted or other host uses the neutral `agent` prefix. An explicit `github.branch_prefix` overrides new-task defaults. New mappings omit that field; existing fixed prefixes, including `codex`, stay unchanged. To adopt host defaults in an existing project, explicitly remove only `github.branch_prefix` in a reviewed configuration change and merge it into the base before new tasks. Existing task bindings retain their recorded branch regardless of the naming policy. Unrecorded local branches using a supported prefix can be recovered; multiple candidates require inspection.

When the user switches agents on one task, continue in its recorded worktree on its recorded branch and update the existing primary PR. Same-machine agents with directory access see the same staged, unstaged and untracked files without an intermediate commit. Inspect those changes and the saved brief/decisions before writing; preserve valid existing scope, baseline and evidence. Access failure requires restoring access or explicit recovery of the original directory. Creating a replacement worktree is not continuation. Conversation history is not transferred by opening the directory, and prior agent implementation choices are distinct from confirmed user requirements.

Each applied `prepare` starts a simple local execution ID unless `--execution-id RETURNED_ID` reuses the current execution. Save the ID in this chat and pass it on subsequent prepares in the same execution. A new chat/agent omits that ID and starts a new one while retaining the same task/worktree/branch/PR. Optionally pass the host's native `--session-id REFERENCE`; the same current host/session reuses its ID automatically. Execution records retain previous executions separately from task evidence. Planning is read-only. IDs identify executions only: they do not detect activity, lock files, transfer authorization or schedule concurrent writers. This workflow assumes serial editing of a task.

## Select and use the workspace

First plan `prepare` to discover an existing task binding. If it reports a recorded/existing task checkout, resume that execution path before creating any new directory. For a new task, when the host provides Codex-managed worktree tools, prefer their attachment/lifecycle support: inspect this chat's artifacts, reuse a suitable task worktree, or create one with the refreshed `origin/BASE` as its starting ref. Then prepare its named task branch using `prepare TASK --repo RETURNED_DIRECTORY --agent HOST --in-place --apply`. That explicit option is for an already selected directory; do not use it in the primary checkout merely because the current branch is clean. If managed tools are unavailable, use the default CLI preparation above. Users can create their chats in the same project themselves; this workflow does not create or message other chats on its own.

**Execution directory:** creating/attaching a worktree does not itself relocate the chat's existing tools. Save the returned path in the chat context. Use it as `workdir` on every terminal call, pass it as `--repo` to every helper, and use absolute paths there for file reads/edits and previews. A `cd` in one shell call does not change subsequent tools. Verify `git rev-parse --show-toplevel` and `git branch --show-current` there before the first write, then record scope and run `write-context`. Always report the actual task directory/branch. On a resumed chat, resolve the task again and run `prepare` to recover its original path; do not infer it from the chat's initial directory.

Keep existing resource ownership rules: dependencies/setup may be needed per directory, and ignored local files do not automatically appear in a new checkout. Inspect project setup instructions and copy only authorized local configuration. Processes, listeners, shared runtimes and test data can still be shared even though Git files are isolated. For a requested manual trial, use [on-demand acceptance environments](acceptance-environment.md) to prepare and verify the result in this task worktree while preserving the primary checkout and other tasks' resources.

## Update from main and resolve conflicts

Before the final verification and merge of a task PR, integrate the freshly fetched base in that task's directory:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py sync-task PROJECT-123 --repo /absolute/task-directory
python3 /absolute/plugin/scripts/plane_workflow.py sync-task PROJECT-123 --repo /absolute/task-directory --apply
```

Plan is read-only and reports only the known base. Apply fetches, rechecks task ownership/scope/cleanliness, then merges the exact fetched base commit into this task branch. It does not push, merge a PR, write Plane state, stash, reset or change another worktree. A clean update produces a local merge commit. Record fresh checks/review and reassess any acceptance/authorization bound to the old head before pushing the task branch and updating its existing PR.

If A merged while B was developing and both changed the same code, `sync-task` leaves B's merge in progress and reports the conflicted paths. Resolve the actual implementation semantics in B, preserving both accepted A behavior and B's requirements; do not choose all of either side automatically. `write-context` permits scoped resolution of a recognized base merge, while review/merge gates remain blocked. Stage only reviewed resolutions with literal task paths, finish that local merge with `git commit`, then rerun `sync-task`, affected tests and review. Read the original user context before rebinding acceptance/merge authorization; material changes still require acceptance under the existing contract. If the conflict changes product behavior ambiguously, ask only for that decision and keep the merge pending.

The scope baseline remains immutable. Scope checks compare task changes against the shared base and account for clean incoming base files during a pending base merge, so A's unrelated accepted files are not adopted into B's allowed paths. B's own edits to those files still block unless independently authorized. Renames, unexpected files and unrelated Git operations require inspection.

The merge gate reads the PR's live base commit and mergeability. An unknown/different live base or a base not yet integrated in the checked task head blocks merge. Refresh/integrate, rerun affected verification and update the same PR. Immediately before merging, repeat the gate and use the exact PR-head guard; GitHub remains authoritative if the base advances again. Never force a conflict through with admin/automatic merge flags.

## Finish one task without disturbing another

Each task has its own PR and completion evidence. `finish-task` updates only the primary base checkout after confirmed PR merge and task completion; it preserves all task branches/directories, including another task's uncommitted changes. If the primary checkout is dirty, divergent or held by another task, task completion remains separate from pending local handoff. Do not switch or clean the other task to make handoff pass. Worktree deletion/archival and moving a chat between checkouts are separate operations with the host's normal ownership checks.
