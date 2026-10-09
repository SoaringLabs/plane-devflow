# Architecture and scope

Plugin distribution is portable `plugin.json`, `mcp.json`, `skills/` and bundled references/scripts. The repository root also contains a local marketplace and an optional composite GitHub Action. Codex executes Skill instructions; deterministic scripts handle Git/config/reporting and REST lifecycle synchronization.

| Responsibility | Owner |
| --- | --- |
| Task requirements and human acceptance | Plane work item and user |
| Implementation and repository checks | Codex plus repo instructions |
| Code state, review and merge evidence | Git/GitHub |
| Stable project/repo/state mapping | `.plane-for-codex.json` in each business repo |
| Interactive credentials | Official Plane MCP OAuth / existing GitHub CLI |
| Unattended synchronization credential | Per-repository GitHub Secret `PLANE_API_KEY` |

MCP uses Plane's official OAuth endpoint. The optional Action uses public Plane REST v2 and its distinct PAT. No plugin-owned backend or credential proxy is introduced. Personal and organization repositories use the same mapping. This v1 supports github.com and Plane Cloud; HTTPS REST origins are configurable for tests/future expansion, but a full self-hosted OAuth/GitHub Enterprise integration is not claimed.

Git side effects are opt-in `--apply`, use argument arrays, and do not reset user changes. New branches require mapping already present in the base commit. Worktrees share the original Git common directory and preserve unrelated changes. Existing PRs are reused, while merged/closed task branches require deliberate follow-up decisions.

The Action runs pinned code, fetches the latest PR snapshot, then reads config from the trusted base commit. It never checks out or executes PR head code. `pull_request_target` supplies base-repository permissions/Secrets; this design still assumes trusted base maintainers and deliberate primary-task references. Config URLs determine where the Plane PAT is sent, so reviewing base config is part of trusting this integration.

Primary task matching accepts `[PROJECT-123]` plus an optional exact binding. Generated reports always include the binding. Cross-repository, cross-workspace/project and multiple-primary references are rejected. One task / one primary PR is the v1 contract, not a multi-PR completion aggregator.

State transitions preserve terminal groups and do not move a configured review task back to development. Merging writes Done only under `on_merge` without the manual label. A merged task under manual policy stays review. Closing an unmerged PR makes no state transition. The lifecycle comment is upserted by `(external_source, external_id)`; per-PR concurrency serialization reduces duplicate writes. No distributed exactly-once guarantee is claimed.

Network calls reject redirects to avoid forwarding credentials elsewhere. API error bodies and Git remotes are not logged. Read operations retry transient failures; ambiguous network failures on writes require inspecting current state before replay. Temporary server errors/rate limits have bounded retries. State writes and comment writes are separate calls; if the second fails, rerun after checking the already changed state.

Validation separates offline behavior, mocked HTTP contracts, real OAuth/read checks, and live external write/Action runs. Only checks actually executed should be reported as passed. An installed plugin can require a new Codex chat to refresh available tools.

Primary references: [Codex plugins](https://developers.openai.com/codex/plugins/), [Plane MCP](https://developers.plane.so/dev-tools/mcp-server), [Plane API](https://developers.plane.so/api-reference/introduction), [GitHub pull_request_target](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target).
