# 0.4.1 credential guidance validation

2026-10-10. Fix the observed initialization gap where choosing Actions ended with a GitHub Secret link instead of guiding Plane token creation first.

- 107 tests passed, including eight new credential-flow tests: current repository binding, read-only page guidance, metadata-only Secret checks, missing Secret recovery without unnecessary PAT creation, permission errors remaining unknown, native mode skipping credentials, changed origin rejection, CLI execution and readiness/installer routing to the Plane stage.
- Package validation, setup Skill validation and whitespace checks passed. Runtime remains Python standard library only.
- Actual Plane desktop UI inspected through the available computer-use tool: user menu → Settings → Personal Access Tokens → Add access token. The unsubmitted form has Title, Description, Expires and Generate token. The settings overlay retains the task page URL, so the plugin does not invent a direct PAT-settings URL. The creation form was cancelled without generating a credential.
- All three credential-guide steps ran read-only against an existing business repository. URLs resolved to its configured workspace and repository; their identities are omitted here. At the time of this check, GitHub Secret-name metadata reported PLANE_API_KEY absent. No PAT value was created, read, copied or transmitted. No Secret or repository file was changed by this validation.
- Browser/computer use is optional host assistance for navigation and non-secret fields, with human handoff for PAT generation/copying and Secret paste/save. A host lacking those tools receives explicit URLs and steps. This is Skill/tool orchestration, not a new browser service or mandatory plugin dependency.
- PR merge authorization is kept separate from credential-stage confirmation; natural user replies can resume each stage.

The full human credential handoff was not executed during implementation. Secret presence remains distinct from runner authentication and real PR writeback. Installation verification is recorded below after the update.

Local plugin installed and enabled at 0.4.1. All 15 package files match source/cache SHA-256. The installed CLI reports 0.4.1 and exposes the plane/github/verify credential stages. The official Plane MCP name and endpoint were retained.
