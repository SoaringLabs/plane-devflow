# 0.9.0 release validation

This release makes user-scope Agent Skills installation the default for Codex, Claude Code, Cursor and OpenCode. `--global` remains in the README command. The complete Codex plugin and its qualified skill identifiers remain compatible; the existing npm 0.8.1 installer is a legacy channel and is not republished for this Skills CLI release.

## Validated scope

The [four-agent matrix](agent-compatibility.md#verification-matrix) records native CLI versions and separates installation, native discovery and MCP configuration from authenticated account access. Pre-release checks use isolated local snapshots; public GitHub installation and CI are separate release checks.

The earlier 0.8.1-based candidate passed 264 Python tests, 18 installer tests, 24 decision-eval structure cases and the real-install suites. See [standalone validation](validation-skills-add.md) for historical evidence and observed failures. Release checks against the 0.9.0 payload passed the 18 npm installer unit tests, real complete-plugin npm/native installation, standalone installation/refresh/removal and the four-agent installation/native-inspection matrix. All 24 decision-eval cases passed structure validation; package validation, generated-source drift detection, Markdown resources and the offline demo passed. All 264 Python regression tests passed on Python 3.14.3 (168.409 seconds).

Three affected decision scenarios (`SETUP-03`, `START-01`, `DELIVER-03`) were evaluated in fresh read-only Codex sessions against the 0.8.1 plugin baseline and the 0.9.0 standalone payload: 3/3 passed for each, with zero critical failures. Both runs used the same rubric digest `3017d63043d0a6534c60116fd21031077e00ed9eb58952987e37674705b662f8`, CLI 0.163.0 and its default model without override, one repetition per case. Captured command events confirm relevant instructions were read; no business operations were executed. This is a synthetic decision smoke check, not multi-host model quality or live account evidence. Baseline payload digest: `f133a176c30963f3b404ee55ac9046986eeaebfb9b9c7274b744d5fc2c3acc61`; standalone eval adapter digest: `1f9435d7bfceceebcad91df282004893a49ce24e3abf0cbd705d235c6d7ebdd4`. Raw traces stay outside the public repository.

The canonical plugin changes only its release version; compatibility installer runtime, configuration schema, sync ownership, task receipts, branch defaults and authorization gates are retained. Each generated standalone skill contains its own scripts/references and native host integration guides.

## Public-source checks

After pushing the reviewed 0.9.0 payload, Skills CLI 1.7.4 installed from the public `SoaringLabs/plane-for-codex` source in all four isolated host profiles. All three skills passed global/project installation, repetition, exact payload and helper checks, and removal preserving synthetic configuration/authentication and business mapping. Native recognition passed for Codex, Claude Code and OpenCode; Cursor skill loading remains login-blocked. Cursor's live MCP recheck failed as recorded below.

A project-scope public-source `skills check` recognized all three tracked skills and reported them up to date; `skills update plane-setup plane-start plane-deliver --project --yes` likewise checked all three and reported no available update. This verifies public tracking and no-change update checking, not installation of a later production payload or rollback. The changed-source reinstall remains a separate local Git fixture result.

## Observed release-check failures

The first cross-platform CI run passed nine jobs but its Windows standalone loader check found no global skills. Codex resolves Windows user skill roots through the native Known Folder API, which ignores the temporary HOME/USERPROFILE used by the installer fixture. Windows native checks now require explicit opt-in on an ephemeral GitHub Actions user and temporarily mount the isolated `.agents/skills` directory at that user's native root using a junction. They refuse to replace any existing skill directory/link and remove only their own junction afterward. Local Windows real-user execution remains blocked by this fixture guard; Unix checks continue using temporary HOME. This is test environment plumbing, not a production installation rewrite. The final CI outcome is linked in the Release.

During public-source verification, Cursor's native MCP list returned connection failure twice, including a targeted recheck with the same empty isolated profile. Earlier local native checks returned `requires_authentication`. File installation and prior configuration recognition remain evidenced; this failed public recheck does not establish current live connectivity or fresh OAuth. Both failures are retained in private diagnostics and summarized in the Release.

## Unverified and limited items

- Cursor native skill loading: the empty Agent CLI profile stops at required client login. File installation and MCP configuration recognition passed, without a skill-catalog result.
- Fresh-client Plane OAuth and authenticated tool access for all four hosts. No real credentials are copied into test profiles; a registered URL or `requires_authentication` result is not a successful authenticated connection.
- Model-driven end-to-end business workflows, multi-host decision quality, real PR writeback/state transitions, Cursor GUI acceptance and remote/cloud/SSH runtimes.
- Cross-platform native Claude/Cursor/OpenCode behavior. CI can verify installation on its operating systems without certifying unavailable native host/model sessions.
- Public-source installation/update tracking and remote CI are checked separately after pushing the reviewed commit. Their final status is recorded in the [GitHub Release](https://github.com/SoaringLabs/plane-devflow/releases/tag/v0.9.0), rather than inferred from local snapshot tests.

## Existing installations

Retain the existing source identity, business mappings and account authorization when updating the complete plugin. Updating that plugin does not install duplicate standalone skills or migrate another agent's credentials. The local update verifies the native plugin version, all three qualified skills, payload hashes and preservation of configuration/authentication. Reopen the app/session after installation to refresh the current tool inventory.
