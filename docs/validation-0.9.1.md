# 0.9.1 release validation

This patch changes installation guidance and release validation, retaining three independent skills. The recommended command installs into the current repository; `--global` is an explicit option. Each repository retains its own Plane mapping. Existing complete-plugin and global installations remain supported without automatic migration.

## Checks for this release

All 264 Python regression tests and 18 compatibility installer unit tests passed. Actual npm/native complete-plugin installation and isolated Skills CLI installation/native Codex discovery passed. Package validation, generated-source drift detection, all 24 decision-eval corpus structure cases, references across 62 Markdown files and the offline demo passed. The four-host isolated installation matrix checks all three skills in project and global scopes, repeat installation and removal preserving synthetic configuration/authentication and business mappings. Native host discovery and account access are reported separately.

The canonical skill instructions, MCP declaration, authorization gates, configuration schema and compatibility installer runtime are unchanged. Runtime payload differences are release version strings and generated distribution versions. No new model decision evaluation is claimed for this documentation patch; the historical decision smoke results remain in the [0.9.0 validation](validation-0.9.0.md).

The isolated macOS checks passed with Skills CLI 1.7.4: all four hosts installed all three skills in both scopes, repeated installation and preserved synthetic settings/authentication and business mappings after removal. Native inspection results for this patch:

| Host | Native skill discovery | MCP evidence in the empty profile |
| --- | --- | --- |
| Codex 0.163.0 | All three passed | Configuration readback passed |
| Claude Code 2.1.301 | All three passed | Configuration readback passed |
| Cursor Agent 2026.10.19-6bbf2c4 | Unverified: client login required | Login/approval blocked the native check |
| OpenCode 1.19.3 | All three passed | Configuration readback passed |

No fresh OAuth completion or model execution is claimed by this matrix. Empty-profile MCP registration/readback is separate from access through the existing authorized connection.

## Release and local update

Remote CI and public-source verification follow the source push. Their final outcomes and run links are recorded in the [0.9.1 Release](https://github.com/SoaringLabs/plane-for-codex/releases/tag/v0.9.1). Local installation uses the existing complete-plugin source and keeps the marketplace identity. Verification compares cached payloads, confirms all three native skills, checks existing settings/authentication hashes and performs a read-only check through the existing Plane connection. No duplicate standalone skills or new account credentials are installed in the real user profile.

The compatibility npm package remains the separately published legacy 0.8.1 channel. This Skills CLI/GitHub release does not require a new npm publication.

## Unverified and inherited limits

- Fresh-profile Plane OAuth and authenticated MCP tool access across the four agents; isolated profiles never receive existing account tokens.
- Cursor native skill discovery and GUI acceptance require client login and remain unverified. The 0.9.0 public-source MCP check returned connection failure twice; this documentation patch does not claim to fix it.
- Model-driven end-to-end workflows, multi-host decision quality, real PR writeback/state transitions, and remote/cloud/SSH execution.
- Native Claude Code, Cursor and OpenCode behavior on Windows/Linux. Installation CI does not substitute for those native host sessions.
- A no-change public update check is not proof of upgrading an older production installation to a later payload; changed-source reinstall is tested separately in a local Git fixture.

Detailed historical host results remain in the [agent compatibility matrix](agent-compatibility.md#verification-matrix). Installation, native discovery, MCP configuration and authenticated use are distinct outcomes.
