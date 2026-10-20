# Skills CLI distribution validation

Status: unpublished local candidate, based on 0.8.1. This record distinguishes candidate installation from the public GitHub source, and dependency metadata from authenticated MCP access.

The default README command now targets the three self-contained `skills/` folders through Skills CLI. The complete plugin and compatibility npm installer remain unchanged. Generated skill resources derive from canonical plugin sources; a read-only drift check protects the committed copies. Generated guides make related workflow instructions available without requiring companion skills to be installed.

## Acceptance checks

- Generate and validate each standalone payload, local Markdown references and anchors, helper startup, vendored synchronization files and MCP dependency metadata.
- Execute actual Skills CLI in isolated user/Codex/npm state. Check selected/global and project installation, a local Git source snapshot, repetition, source/cache removal and each individual skill.
- Ask the actual Codex native loader for the three standalone skill names, English UI metadata, declared dependencies and loader errors. Check compatible plugin-qualified skills separately.
- Register the declared MCP endpoint only in the temporary profile, read back native configuration and probe the public transport without credentials. Report actual authentication requirements separately from registration or metadata.
- Retain hashes of real configuration/authentication and the original local plugin before and after. Do not copy credentials into the test profile or publish this candidate.

Results and limits are filled from completed checks; pending checks are not passing evidence. Raw local paths and response records stay outside the repository.

## Completed local results

- Python 3.14.3: 261 tests passed (187.229 seconds), including six standalone generation/isolation regressions. The existing package validation suite's 18 tests also passed separately.
- Node.js 24.15.0: 18 compatibility installer unit tests passed. Package validation confirms the three plugin entry points and three generated standalone entry points; all three Skills Creator frontmatter checks passed. All 24 existing decision-eval cases passed structure validation; no new model decision scores are claimed.
- Node.js 22.20.0 also passed the actual Skills CLI installation/native-loading suite, including changed-source refresh and removal preserving MCP configuration; its live network probe was disabled.
- Actual Skills CLI 1.7.4 installed this unpublished candidate from a temporary local Git snapshot. Global installation, project-selected installation, each of the three skills alone, repeat installation and refresh from a changed Git commit passed. Source and npm cache were deleted before reloading; all three skills still loaded, and every installed skill file matched its candidate payload.
- Codex CLI 0.163.0's native loader returned `plane-setup`, `plane-start`, `plane-deliver`, their English UI names and the Plane streamable HTTP dependencies, all enabled with no loader errors. These standalone names are distinct from the compatible plugin-qualified names.
- Skills CLI left the empty Codex configuration and MCP registry unchanged. Native `codex mcp add` registered Plane in the temporary profile and initiated OAuth. The test ended the empty-profile consent wait after 20 seconds, then read back the enabled endpoint with the native CLI. A credential-free initialize request returned HTTP 401 with an OAuth resource-metadata challenge. Removing skills preserved that temporary MCP registration.
- Separately, the existing authenticated Plane MCP completed a read-only workspace retrieval over OAuth. This verifies preservation of the current connection; it is not an authenticated call from the empty test profile. No credentials were copied and no business writeback was attempted.
- The original npm/native plugin installation integration passed again, including full payload hashes, three plugin-qualified skills, repeated installation after npm-cache deletion, read-only inspection and retained custom source. Canonical plugin files and the primary checkout remain at the released 0.8.1 content.
- The macOS integration sandbox denied writes under the real user directory and reads of real configuration, file authentication and Keychain paths. Real Codex configuration/authentication and npm configuration hashes were unchanged. The primary checkout's existing untracked AGENTS file was preserved. Child HOME/CODEX_HOME/npm state were temporary; no real-profile migration occurred.

## Observed failures and limits

The first package regression run found that generation treated illustrative links inside fenced examples as resources; generation now preserves fenced examples and the full suite passes. The initial live integration waited for native OAuth instead of completing unattended; it was stopped and retained as failed evidence. Subsequent tests explicitly report registration and the interrupted consent wait separately from account authorization.

Skills CLI's `update` probe reported no tracked skills for the local file Git fixture. Its zero exit status was not counted as an update pass. Refresh was instead verified by committing a synthetic reference change, rerunning `skills add`, checking installed bytes, and restoring/reinstalling the reviewed candidate. Automatic update tracking for the public GitHub source remains unverified until an authorized publication.

The public `SoaringLabs/plane-for-codex` command still resolves released source; the candidate command's GitHub source argument was replaced with the isolated local snapshot for these checks. No candidate source, npm package, tag or Release was published. Added cross-platform Skills CLI CI jobs have not run remotely. The empty test profile did not complete browser OAuth, so fresh-profile authenticated MCP access and business writeback remain outside these results. The existing plugin's prior model eval results are historical evidence, not new standalone model eval scores.

## Four-host extension — 2026-10-20

The default now offers Codex, Claude Code, Cursor and OpenCode interactively. Each self-contained skill includes common capability/MCP instructions and four host-specific guides. Optional Codex UI/dependency metadata stays in `agents/openai.yaml`; generic workflow names do not assume its dollar invocation syntax. The canonical plugin, npm installer runtime, mapping schema, branch defaults and authorization gates remain unchanged.

The completed local matrix used Skills CLI 1.7.4, Node.js 24.15.0 and Python 3.14.3 on macOS arm64. Separate HOME, XDG, Codex, Claude and npm state prevented real account reuse. The macOS sandbox denied real-home writes, real configuration/authentication and Keychain reads, and access to the Keychain service. Protected real configuration/authentication hashes were unchanged after the matrix.

For **each** host, the actual upstream CLI installed all three skills globally and into a project, repeated global installation, compared every installed file against the candidate, and ran every skill's installed helper. Before host-native configuration checks, installation left synthetic settings, auth files and business mappings unchanged. Removal then preserved the synthetic MCP registrations, retained unrelated configuration, auth files and mapping. These checks cover file installation and runtime startup; the [compatibility matrix](agent-compatibility.md#verification-matrix) distinguishes native loading from model execution.

- **Codex 0.163.0:** native loader discovered all three skills and parsed dependencies; native MCP configuration readback passed.
- **Claude Code 2.1.301:** native initialization listed all three skills and slash commands before returning the expected unauthenticated-model error. Native user-scope HTTP MCP add/get recognized Plane and retained the synthetic existing server. This is actual native skill discovery, without a completed model response or Plane OAuth.
- **Cursor Agent 2026.10.19-6bbf2c4:** native MCP list recognized the isolated Plane configuration and reported `requires_authentication`; the unrelated server remained. Native model/skill inspection stopped at required Cursor login. Skill placement and payload are verified; native loading remains unverified. Cursor desktop 3.25.9 was inspected for CLI capabilities only, not GUI acceptance.
- **OpenCode 1.19.3:** native `debug skill` discovered all three skills; `debug config` parsed the remote Plane endpoint and retained the disabled unrelated server. Native MCP list reported that Plane needs authentication. No provider login or Plane consent was performed.

264 Python tests passed (182.978 seconds), including nine standalone regression tests. A doctor regression verifies operation without Codex or GitHub CLI on PATH. The 18 npm installer unit tests and all 24 decision-eval structure cases passed. The Codex standalone real-install suite passed again after the host extension, including individual skills, changed local Git source reinstall, deletion of source/cache, native loading and removal preserving MCP. Its live OAuth/network probe was disabled on this rerun; the earlier transport results above remain separate historical evidence. Source/package validation, generated-output drift detection and local Markdown links passed.

Two initial matrix runs failed because test assumptions expected Cursor/OpenCode-specific global directories. Actual Skills CLI 1.7.4 installs both into shared `~/.agents/skills/`, supported by both hosts. Tests and guides now record the observed paths; the final full matrix passed. The initial Cursor archive request returned 403 through Python's downloader; downloading through the official installer's curl route succeeded. No user-level tool installation or account settings were changed.

Unverified items: Cursor native skill loading; authenticated Plane access from each fresh client; model-driven workflow/decision quality on all four hosts; real PR/state writeback; Cursor GUI, remote/cloud/SSH runtimes; Windows/Linux native hosts; public GitHub install/update tracking; and the newly added remote CI jobs. No source, npm package, tag or Release was published, and the user's existing plugin installation was not migrated.
