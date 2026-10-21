# Your first project with Plane DevFlow

[简体中文](first-project.zh-CN.md) · [Installation](installation.md)

Start here if you have an agent but no prepared repository or Plane connection. These instructions work before the skills are installed: open a parent folder where you want the project, then give the agent this prompt. Replace the project name and describe your own goal.

> I want to create MyTodo, using Plane for tasks and GitHub for code. Follow https://github.com/SoaringLabs/plane-devflow/blob/main/docs/first-project.md and its first-project workflow. Inspect this computer and existing connections first, then propose one preparation plan with the local folder, repository visibility, installation scope and missing tools. Execute only the plan I approve. I will handle account login and credentials. Do not build the app yet.

The agent should read the [first-project workflow](../plugins/plane-devflow/references/first-project.md). Before installation it can perform normal read-only environment checks and guide the approved preparation; it cannot invoke an uninstalled skill/helper. This guide does not install anything itself. Once available, plane-setup continues the same workflow. Pick either standalone skills or the Codex plugin, keeping existing working connections.

| Step | Agent handles | You handle |
| --- | --- | --- |
| Preparation | Detect missing tools; propose folder/repository/account choices; prepare only the approved setup | Confirm the concrete plan; installer/admin prompts and missing Git identity |
| Accounts | Start GitHub and Plane connection flows; verify the actual account/workspace | Registration, login, OAuth, workspace creation if needed |
| Repository and skills | Create/clone the approved repository, initial commit and install the selected channel; check discovery | New chat only when loading is stale; use the supplied continuation text |
| Project and sync | Associate the selected project, prepare configuration PR, verify background connection | Choose/approve the project; enter credentials yourself; review and authorize setup PR merge |
| First tasks | Draft scope and acceptance criteria from your idea | Review the exact list before any tasks are created |

Ask “Continue setting up MyTodo” after an interruption. The agent rechecks current state and resumes the missing step; it should not recreate a repository/project or request another token merely because you changed chats. A copyable handoff supplies the target and next action. Prior approval must be recovered from original user messages, not inferred from that handoff. If those messages are unavailable, confirm only the concrete missing decision.

After setup, describe the first version:

> Plan the first version: add, complete and delete todos; keep them after refresh. No login or cloud sync. Show me the tasks first without creating them.

Then, after reviewing the actual draft:

> Create this list in the selected Plane project. Stop after returning the real task links.

Or explicitly include “and start the first task” when you want implementation too. Task creation/readback is followed by the existing isolated-worktree workflow; no task number needs to be invented in advance. Saved drafts and partial creation can be resumed through [task planning](../plugins/plane-devflow/references/task-planning.md).

Setup is complete only when the selected background integration is verified. Real PR-event writeback is checked separately during actual delivery. New basic mappings preserve task states; this guide adds no state automation and changes no acceptance, merge or local finalization rules. PR delivery does not imply a running preview: ask for a trial when you need one, and keep merge authorization explicit.
