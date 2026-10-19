# 0.7.0 validation

Scope: independent tasks in multiple chats of one project, fresh configured-base branches, individual task PRs, and resolving base conflicts before merge. The configured base is normally `main`; existing project mappings, acceptance, merge authorization and Plane synchronization ownership remain intact.

## Requirement coverage

| Requirement | Evidence |
| --- | --- |
| Different chats in the same project can work on different tasks | Default `prepare` allocates distinct worktrees without switching the primary checkout. Real-Git tests start A/B concurrently and start C from dirty B; Codex-style detached worktrees also prepare concurrently. The Skill uses host-managed attachments when available and explicitly routes every tool to the returned execution directory. |
| Each new task starts at main | Apply fetches the configured origin base before creation. Tests advance a real local bare origin while the primary is stale, then verify new task and detached-worktree branches start at the fetched main commit. |
| Tasks develop on independent branches | A/B/C get separate named branches, indexes and files; edits and commits stay in the selected worktree. Resume recovers the original recorded directory, baseline and scope. Detached unique work is preserved rather than overwritten. |
| Each task delivers a PR to main | Both A and B push their own actual branches to the bare origin. The GitHub CLI contract fixture verifies each PR targets main with its own head/task binding. Existing delivery, review and acceptance tests continue to apply. |
| B resolves conflicts after A merges, before B can merge | A is squash-merged into the real bare-origin main. B's base merge leaves conflicts only in B. Scoped resolution combines A/B behavior, blocks review/merge while pending, preserves original scope, invalidates old evidence, and can then be squash-merged with both behaviors retained. Live-PR gate fixtures reject unknown/changed base commits and a base not integrated in the checked task head. |

Task completion is also exercised with A's merged-PR/completed-task fixtures and a real fetch/pull of main while B remains dirty. A's handoff preserves B's branch, head and uncommitted content. PR/Plane snapshots in this test are synthetic; no real service state is changed.

## Forward verification

An independent agent followed the updated Start/Deliver skills using temporary Git repositories and a local bare origin, stubbing only repository identity. It verified default isolation, starting C from dirty B, preserving dirty primary/other tasks, path recovery, fresh base selection for detached managed-style checkouts, A's squash merge, B's conflict/scope handling, stale check/review/acceptance/authorization evidence, verification on the resolved head, and preservation of both task behaviors after B's squash merge.

The forward check did not create real Codex chats, PRs or Plane items. Multiple user-created chats and host-managed worktrees are existing Codex features; this plugin supplies task routing and Git workflow rules. Automated fixtures exercise the corresponding checkout/branch primitives rather than the desktop UI itself.

## Local verification and installation — 2026-10-19

- Full suite: 227 tests passed (212 existing, 14 parallel/worktree integration cases, and one additional live-base merge-gate case).
- Both updated Skills passed `quick_validate.py`. Package manifests/versions, Skill reference links and mapping examples passed `validate_package.py`; `git diff --check` passed.
- All nine plugin Python scripts parse under Python 3.10 grammar. Tests ran on the local Python 3.14 runtime; this is not a Python 3.10 runtime or remote CI result.
- Local plugin 0.7.0 is installed and enabled. All 25 portable files match source/cache SHA-256, and the existing root MCP configuration digest is unchanged. No login/credential update was performed.
- All 14 parallel integration tests passed again with the installed helper modules preloaded and their cache paths asserted. This covers both default and managed-style worktrees, two task PR contracts, conflict resolution, evidence invalidation, and A's completion handoff preserving dirty B.
- The installed CLI reports 0.7.0; its legacy offline demo passes without live services. The installed GitHub CLI accepts the live PR `baseRefOid` field used by the new gate.
- New chats can load the updated Skills. No other project configuration, copied Actions script, real Plane item or real task PR was changed during verification. Source publication and remote CI are separate steps.

## Operational boundaries

- Creating a worktree does not relocate the chat's existing tools. The Skill requires explicit terminal workdir, helper repo and absolute file paths, checked against actual Git root/branch. Skill invocation remains model-selected rather than a global filesystem interceptor.
- Default helper worktrees and Codex-managed attachments use the same task checkout records. Native worktrees retain host lifecycle ownership; deletion, archival and moving a chat are separate operations. Missing or migrated bindings require inspection/recovery.
- `sync-task` performs only a local base merge in the selected task checkout. It never pushes, writes Plane, merges a remote PR, stashes or changes another task directory. Conflict resolution still requires code understanding and project verification; product ambiguity remains a user decision.
- The merge gate is read-only and checks live PR base/head/mergeability plus current evidence. If main advances after a gate, repeat the check and rely on GitHub's atomic conflict/protection checks; do not bypass with admin/automatic merge flags.
- Runtime resources and ignored configuration are not isolated by Git. Existing ownership rules still govern local setup, services, ports, simulators and cleanup. This release does not add a scheduler or automatic task/chat creation.
- Base integration keeps the original baseline/scope, comparing the task's current net difference against its shared base and excluding clean incoming base files during resolution. This does not prove semantic ownership within a permitted file; diff review remains required.
