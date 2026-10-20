# Prepare an acceptance environment on demand

Read this when the user asks to run or try a task's result for manual acceptance, or when an agreed delivery includes a runnable handoff. Delivering a PR alone does not require starting an environment. If the user will test later, leave the task ready for this step and report that the environment has not been started.

## Establish the task and version

Recover the selected task's recorded execution directory using `prepare` in plan mode, then inspect `task-context`, its actual Git root, branch and commit. For a linked PR, read its live head and establish that the intended version is present in this checkout. Resolve drift before presenting a result for acceptance. Use this task directory explicitly for setup, launch and verification; attaching a worktree or opening a PR does not relocate an existing terminal or running application.

Inspect uncommitted source changes too. If the source differs from a delivered PR, report the mismatch and keep acceptance of that PR pending; updating it uses the separately authorized delivery workflow. A user-requested work-in-progress trial may include uncommitted changes, but label it as a preview and describe that difference rather than recording acceptance against an unchanged commit.

Keep the primary checkout and other tasks' workspaces unchanged. The default is to run the selected task in its existing worktree, not to switch the primary checkout to its branch. A request to prepare acceptance grants the necessary local setup and execution, not merge authorization, a new delivery, or broader implementation scope. Repository edits still use the existing scoped write preflight.

## Choose the project's acceptance method

Inspect the project's instructions, scripts and existing runtime configuration. Let the project determine the required tools and dependencies, and whether the user needs a running entry point, an executable command, or a generated artifact. Configure only the local prerequisites needed for that method; retain the repository's credential and test-data boundaries.

Inspect existing resource ownership and occupancy before launching. Worktrees isolate source files, while processes, listeners, shared runtimes and test data may still be shared. Reuse an existing resource only after verifying that its source/version and intended use fit this task. Otherwise allocate independent resources where supported. When an exclusive resource is occupied, preserve its current owner and resolve only that contention; do not stop or repoint another task's resource to make this handoff succeed.

Run the required setup and launch/build commands from the task directory. Follow the project's own build requirements when the existing runtime cannot execute the selected version. Use the project's own tooling and runtime selection.

## Verify and hand off

Before saying the result is ready for the user:

1. Confirm that the chosen entry point or command works, or that the artifact opens as intended. A successful launcher exit alone is insufficient.
2. Establish that the running result or artifact comes from the selected task version. Observe a changed behavior/output that distinguishes it from the base, or inspect build/runtime provenance that identifies the intended checkout and commit. If the result still uses another checkout or an older build, correct the routing/build and verify again.
3. Exercise the acceptance path far enough to establish that the user can reach the changed behavior. Report remaining account, data or external-service requirements separately. Keep the task unaccepted when source identity or usability remains unverified.

Give the user the task, actual directory/branch/commit, usable entry point, short acceptance steps, remaining verification limits and resource retention boundary. A command or artifact can be the entry point; every project does not need a persistent service.

Record non-secret setup/launch commands, entry point and observed source/version proof in the existing `environment` evidence. Record any executed checks against the current head and brief in `checks`, following [task execution](task-execution.md). These records declare what the agent observed; they do not supply human acceptance or merge authorization.

Keep resources needed for the user's requested acceptance session available through that session. Record agent-owned resources as `keep` with the agreed handoff and retention boundary in evidence; the request to try the running result supplies that session's purpose. If retention is not possible, provide a verified restart path and state clearly that the entry is no longer live. Do not announce a live handoff and immediately clean it up.

## Resume, feedback and cleanup

On a resumed acceptance request, recheck the intended task version, resource identity and current availability before reusing a previous entry point. A saved process identifier, URL or successful past launch does not establish current readiness. A new task commit requires rebuilding/reloading as appropriate and verifying the result's source again before handoff.

Apply feedback in the same task workspace and deliver changes through the existing task PR. Reassess affected checks and acceptance after changes; setup success and agent verification remain separate from the user's acceptance. Follow [plane-deliver](skill-guides/plane-deliver.md#record-acceptance-or-finalize) for acceptance, merge and completion.

When the session ends, clean up only the agent-owned resources whose agreed retention has ended, verify their identities before stopping them, and update `environment`. Preserve user/existing resources and the task checkout. If the user explicitly wants a different checkout or a permanent environment, handle that as a separate handoff rather than silently moving this task or changing its binding.
