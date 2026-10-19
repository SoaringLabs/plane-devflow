# 0.6.1 validation

Scope: task ownership before the first repository artifact write, including requirement plans and research notes. Multi-task orchestration, state configuration, acceptance/merge rules and completion handoff remain outside this change.

## Local verification — 2026-10-19

- `python3 -m unittest discover -s tests -q`: 212 tests passed (195 existing and 17 first-write cases).
- First-write cases use real temporary Git repositories. They cover discussion without task selection, planned document writes on the base/another task branch, missing task identity, scope before file creation, scoped document work without implementation receipts, resumed accumulated changes, detached HEAD, configured non-main base, preserved files/metadata, ignored artifact paths, symlink files/parents and CLI exit status.
- New-task preparation is exercised from an existing task branch: the new branch starts at the configured base and preserves the original branch's commits.
- Independent forward-testing exercised four requests in isolated synthetic repositories: discussion only; saving a new task report while an old task has dirty files; resuming the report in a new chat; and a new plan with no task identity. The checks preserve discussion-only intent, task ownership and the existing checkout-isolation behavior.
- That review exposed ignored-file carryover and an in-repository symlink targeting an out-of-scope file. Both were corrected and independently rechecked; tracked files remain writable when later ignore rules match them.
- Package manifests, versions, Skill reference links and mapping examples passed `scripts/validate_package.py`. The updated Skill passed `quick_validate.py`; its YAML dependency was provided through a temporary `uv` environment, with no global Python dependency change.
- All eight plugin Python scripts parse under Python 3.10 grammar. Execution used the local Python runtime; this is not a Python 3.10 runtime or remote CI run.
- The offline demo passed without live Plane/GitHub calls. `git diff --check` passed.

## Local installation

- Reinstalled `plane-for-codex@plane-for-codex` from the existing local marketplace. Inventory confirms version 0.6.1, installed and enabled.
- All 23 portable plugin files match source/cache SHA-256. The existing root MCP configuration digest is unchanged; no login or credential change was performed.
- The installed CLI reports 0.6.1 and its offline demo passes. An installed-CLI smoke test blocks a planned document on the base branch, then passes after preparing the selected task branch and recording document scope; the preflight itself creates no document.
- New chats load the updated Skill package. Existing chats may retain their previously loaded descriptions/instructions.

## Boundaries

Skill discovery descriptions now include mapped-repository requirement discussion, research and planning. The Skill invokes the read-only write preflight; this package does not install a global filesystem/editor interceptor or guarantee invocation by every model/client. The forward tests validate the workflow once loaded, rather than measuring automatic Skill selection across clients.

The helper checks task checkout/scope and concrete planned paths, not the authenticity of task selection or semantic ownership within an allowed file. The agent must establish these from the user's request and verified context. Remote-base freshness is established separately before branch preparation; `write-context` itself never fetches and reports freshness as unverified.

Directly authored ignored artifacts and symlink paths require an external temporary location or an actual trackable scoped path. Existing ignored dependencies/build caches are not inventoried or modified. A document-only request does not require implementation/design evidence or authorize implementation/state transitions.

No real Plane task was mutated and no production PR was opened, merged or published to test this update. Source publication, release tags and remote CI are separate operations.
