# Review the first-project onboarding candidate

Use the PR checkout for this review. Public installation commands and kickoff prompts pointing at `main` continue to use the released source until this change is merged/published. Loading a skill from this checkout is a source-payload review, not proof of installation/native discovery on a new computer. No global skill replacement is needed.

Executed checks and remaining limits are recorded in [candidate validation](validation-first-project.md).

## 1. Review the user journey

Read [the Chinese first-project guide](first-project.zh-CN.md) or [English guide](first-project.md). Check that local preparation, account handoffs, project/sync configuration and first-task planning form one sequence, with a specific next action after each interruption. Check the agent/user division against [the agent workflow](../plugins/plane-devflow/references/first-project.md).

## 2. Try read-only preparation

In a fresh agent chat, provide the absolute path to this checkout's `plugins/plane-devflow/skills/plane-setup/SKILL.md`, then ask:

> 请使用这个本地 skill，帮我准备第一个 Plane 项目。目标是一个尚未创建的临时目录。先检查并给准备方案，不要安装工具、创建仓库或进行任何远程写入。

Expected: a preparation plan and the next action, without requiring a preexisting task/mapping or treating installed app/CLI/config files as live account access. The read-only helper can be exercised from this checkout:

```sh
python3 plugins/plane-devflow/scripts/plane_workflow.py bootstrap-status \
  --repo /tmp/plane-devflow-review-new-project --channel installed
```

The target should remain absent. The JSON handoff's `resume_prompt` can be copied to another chat; the next chat must recheck the target/current facts and recover actual approvals before any write.

## 3. Try first-task drafting

In a fresh chat, provide this checkout's `plugins/plane-devflow/skills/plane-start/SKILL.md` path, then ask:

> 我想用 Plane 管待办网页的第一版：添加、完成、删除，刷新后保留，不做登录。先列任务给我看，不要创建、不写文件。

Expected: a small task list with scope/exclusions and observable acceptance criteria. No task identifier, mapping or login is required for this chat-only result. Creation is a separate decision after reviewing that exact list; task creation alone must stop before implementation.

## 4. Exercise recovery without account writes

These tests use disposable Git repositories and synthetic project snapshots:

```sh
python3 -m unittest discover -s tests -p 'test_first_project.py' -v
python3 -m unittest discover -s tests -p 'test_task_planning.py' -v
```

They cover missing tools/repository, parent-repository isolation, saved-draft recovery in another process, lost create replies, partial success, same-title conflicts, stale/incomplete/wrong-project snapshots and preservation of existing state policy. The helper only prepares creation operations; it never creates a Plane task itself.

## Remaining live acceptance

Fresh-machine installers, browser OAuth, native skill loading in every host, and real MCP creation/readback are separate live checks. In a disposable Plane project, approve a concrete task list before any create; verify external correlation fields round-trip before claiming retry recovery. Active and archived items must be reconciled. Concurrent creators can still race; the plan helper does not provide server-side uniqueness.

State management, task completion policy and local finalization remain unchanged. Keep this PR open until the requested human review is complete.
