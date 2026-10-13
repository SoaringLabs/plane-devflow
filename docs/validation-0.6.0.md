# 0.6.0 validation

Scope: task checkout/file-scope checks and automatic primary-base handoff after confirmed task completion. Requirement persistence, preview redesign, custom state rules and background services remain outside this change.

## Local verification — 2026-10-13

- `python3 -m unittest discover -s tests -q`: 195 tests passed (171 existing and 24 checkout/handoff cases).
- New checkout cases exercise explicit scope setup, committed/staged/unstaged/untracked changes, rename endpoints, paths with spaces, branch/directory drift, history rewrites, stale scope plans, Draft guard enforcement, concurrent scope updates and early normal/squash integration.
- New handoff cases use real temporary Git repositories and a local bare origin for fetch/switch/pull. GitHub PR/required-check responses and repository identity are fixtures; no live GitHub or Plane writes occur.
- Handoff cases cover latest base after squash, later unrelated base commits, repeat execution, fresh completed-task snapshots, dirty checkouts, unique/divergent base history, absent local base, worktree ownership/primary handoff, Git operations in progress, fetch/pull failures and retry, concurrent checkout changes, missing merge content, symlink/lock conflicts and a configured `trunk` base.
- `python3 scripts/validate_package.py`: plugin manifest/version, Skill references and mapping examples passed.
- Offline demo passed without contacting live services.
- All eight plugin Python scripts parse under Python 3.10 grammar; execution used the local Python runtime. This is not a Python 3.10 runtime or remote CI run.
- `git diff --check` passed.

## Installation

- `codex plugin add plane-for-codex@plane-for-codex --json` installed 0.6.0 from the existing local marketplace.
- Inventory confirms installed=true and enabled=true; the installed CLI reports 0.6.0.
- All 23 portable plugin files match source/cache SHA-256, including the Plane MCP definition. Existing root MCP configuration is unchanged; no login or credential update was performed.
- The installed CLI's offline demo passes its review and checkout gates without contacting live services.
- Open a new application-repository chat to load the updated Skills; existing chats may retain the previous package context.

## Boundaries

Path checks do not prove semantic task ownership within a permitted file; scoped diff review remains required. Remote-base freshness is refreshed by the Skills at preparation/resume and before delivery, while gates themselves stay read-only. The Skills invoke context checks before edits/commits; the package does not install a global editor/file-system interceptor.

The local handoff is separate from completion evidence and leaves completed Plane state unchanged on failure. It preserves task branches/worktrees; updating a primary checkout does not move an existing worktree chat. A new task still fetches the configured base before preparing its branch.

No production PR was merged and no real Plane task was changed to test this version. Local Git integration tests do not certify every host, network policy or representative conversation. No public release/tag or remote CI is claimed by these local checks.
