# Setup reference

The script path is `<plugin-directory>/scripts/plane_workflow.py`. Resolve it from the installed Skill, not from the user's repository. Python 3.10+ and Git are required; `gh` is required for PRs and repository Secrets.

## Authenticate and resolve mapping

The human entry point is selecting **Plane: 初始化** in Codex's skill selector and sending that selection; a Skill-only message starts setup. A short natural-language request also works. The commands below are agent-operated implementation details. Resolve their arguments automatically; show only meaningful choices and the resulting association to the user.

1. Use Codex's bundled `plane` MCP connection. It targets the official OAuth endpoint `https://mcp.plane.so/http/mcp`. Browser consent selects a workspace; use `workspace` / `retrieve` to read that connection's slug and identity. If the user supplied a different workspace URL, resolve the mismatch. Reuse existing consent, reconnect only when necessary. Never ask for an OAuth token in chat.
2. Confirm `gh auth status` succeeds. Both personal and organization repositories use the same repo-scoped commands. Organization ownership does not bypass SSO or repository access restrictions.
3. Discover Plane project/state IDs via available MCP tools, following their actual schemas and pagination. Do not invent UUIDs. Prefer a valid existing mapping or explicit task/project context; otherwise a unique exact match to the origin repository name may resolve the project. If ambiguous, offer a concise project-name selection. Distinguish state groups and names; map a started/development state, a separate review state, and a completed state. If review is missing, explain the needed state and create it only within setup authorization; if the user's scope leaves that choice unresolved, ask specifically about adding that state. Preserve any existing state.
4. For a new mapping, use basic mode and `manual` completion without asking the user to choose modes or type settings. Apply explicit preferences if given, and preserve configured choices on reruns. Enabling Actions or changing to `on_merge` is a later request. Resolve the base branch from the existing mapping or the actual GitHub default branch (`origin/HEAD`, or GitHub repository metadata); `main` in the example below is illustrative.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py doctor --repo /absolute/application/repo
python3 /absolute/plugin/scripts/plane_workflow.py configure \
  --repo /absolute/application/repo \
  --workspace WORKSPACE_SLUG --project-id PROJECT_UUID --project-key PROJECT \
  --in-progress DEVELOPMENT_STATE_UUID --in-review REVIEW_STATE_UUID --done DONE_STATE_UUID \
  --base main --completion manual
```

Inspect this plan, then repeat with `--apply` to write `.plane-for-codex.json`. Existing identical config is reused. Different config is never overwritten by this command; inspect and edit it deliberately, retaining unrelated fields/files. Include mapping in the setup commit/PR and merge it into the base branch before task branch creation. The script checks this prerequisite so isolated worktrees receive the mapping.

State IDs above are placeholders resolved at runtime. A project ID is stable, while the task key is a human-friendly reference. No user's project is built into the plugin. Custom HTTPS API/app origins are configurable; OAuth support for self-hosted installations is outside v0.1.

## Optional event sync

Use a published repository root Action pinned to an exact commit SHA. Resolve the actual published SHA with GitHub; never supply a made-up SHA or a local-only commit. Add this argument to configure:

```text
--action-source owner/plane-for-codex@FULL_40_CHARACTER_COMMIT_SHA
```

This generates `.github/workflows/plane-for-codex.yml`. Existing differing workflow is preserved. For an existing basic mapping, configure with the same fields plus action source; only the new workflow is written.

The Action reads the mapping from the current PR's **base commit** using GitHub's contents API. It runs the pinned Action code without checking out any PR code. Repo permissions are contents/read and pull-requests/read. PRs without a task reference are skipped. Workflow runs for the same PR are serialized, and the Action reads the latest PR state before writing back.

Create a Plane personal API key in the user's Plane account settings. Store it as repository Secret `PLANE_API_KEY`, either in GitHub's repository settings or by running this helper in a human-operated interactive terminal:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py set-secret --repo /absolute/application/repo
```

The input is hidden; the helper sends it through stdin to `gh secret set`. Never type the key into chat, code, config, shell arguments or logged commands. In Codex, open a terminal for the user to run this command if supported. A repository Secret works for both personal and organization repos, including private repos where an organization-wide Secret may not be available on GitHub Free. Check Secret presence by its name only.

Plane REST uses a separate PAT with `X-Api-Key`. It cannot reuse MCP OAuth consent. Repository collaborators who can modify trusted base-branch workflows/configuration must be trusted with that secret. V0.1 assumes one trusted primary PR per task; fork contributions require review of the primary task reference before merge.

Once configuration/Action is merged and the Secret is set, inspect the first run. A passing offline demo does not prove Free-plan REST write permission. On HTTP 402/403, report the actual restriction and retain working basic mode. Credentials/settings are the user's; publishing this open-source repository does not give others access to the author's accounts.
