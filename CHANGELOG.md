# Changelog

Implemented changes by plugin version. See each version's validation record for verification scope and known limits; an entry here does not imply that a GitHub Release or version tag was created.

## Unreleased — 0.14.0 candidate

- Use one product version for skills, local tools and the public synchronization Action, with committed-source release manifests and an explicit stable distribution channel.
- Generate a small project workflow pinned to the product Action instead of copying Python synchronization scripts. Preserve recognized legacy deployments and customized files for explicit migration.
- Add a scoped, resumable upgrade flow for release selection, source verification, isolated project diffs/PRs, installation refresh, activation checks and reverse rollback diffs.
- Keep native integration ownership, existing configuration formats, task bindings and state policies. This candidate does not migrate business repositories, publish a Release/tag/npm package or activate the stable branch.


## 0.13.0 — 2026-10-22

- Expire synchronization connection evidence after 24 hours and share a daily metadata-probe cache across worktrees. Successful and failed routine probes both enter cooldown; local doctor checks remain offline, and expiry does not dispatch a connection workflow or stop independent development. Explicit refresh remains available.
- Add read-only `task-status` diagnosis for checkout/head, requirements/check freshness, PR/CI, Plane snapshots, declared writeback, acceptance/merge declarations, environment and local handoff. Default diagnosis makes no remote request or cache write; explicit refresh never performs repair, fetch, dispatch or business-state changes.
- Add five opt-in model execution evaluations using disposable Git repositories, synthetic GitHub CLI and Plane stdio MCP, grading actual effects and readbacks. Freeze evaluation inputs before sessions, preserve failures/timeouts/unrun cases and keep model execution out of default CI. Clarify active and archived reconciliation before recovering first-task creation, and calibrate documented equivalent decision routes while preserving original scores.
- Align English/Chinese entrypoints and architecture with approved first-task creation, basic mapping state preservation, evidence depth and host-owned session portability. Multi-host and automatic-credential compatibility remain maintenance boundaries.
- Keep the synchronization bundle at 0.10.1 byte for byte; no business-repository sync upgrade is required. See [0.13.0 validation](docs/validation-0.13.0.md) for executed checks, retained failures and unverified scope.

## 0.12.0 — 2026-10-21

- Add explicitly authorized PAT creation from an existing macOS Plane App Cloud session, followed by native Keychain storage and identity/project/expiry verification. No console, clipboard transfer or terminal input is needed for this supported path; credential values stay inside the helper process.
- Bind each plan to the verified account, project mapping, explicit expiry and operation UUID. Require separate replacement intent for existing local credentials; preserve pending entries and metadata-only receipts for recovery, and reconcile ambiguous creation requests instead of blindly creating duplicates.
- Report missing/expired login, account mismatch, permission/network failures, unsupported session layouts and unavailable Keychain access separately. Prompt users to log in to Plane App when needed; unknown/encrypted session formats and other platforms retain the manual credential route.
- Preserve manual credential transfer and GitHub Secret upload boundaries, existing project configuration and account authorization. The GitHub synchronization bundle remains 0.10.1; this release requires no business-repository sync upgrade. See [0.12.0 validation](docs/validation-0.12.0.md) for checks, live acceptance, test cleanup and limitations.

## 0.11.0 — 2026-10-21

- Guide a first project continuously from an empty directory through prerequisite checks, repository preparation, existing account connections, Plane association and background synchronization. Present one preparation plan and only the next necessary human handoff; application development remains a separate step.
- Add read-only `bootstrap-status` and portable setup handoffs with the target directory, current mapping and a copyable resume prompt. Resume by checking current evidence and reusing existing resources and original user decisions, without treating stored progress as authorization.
- Draft a first-version task list in chat before any task creation. Add immutable, mapping-bound task plans, exact-list approval boundaries and reconciliation for partial creation, lost replies and conflicting existing items. Plan persistence and helpers alone never create remote tasks.
- Preserve the three public skills, existing configurations and authorization, state-management ownership, human acceptance, merge gates and local finalization. The independently versioned GitHub synchronization bundle remains 0.10.1, with no version-only business-repository upgrade.
- Publish English changelog entries and establish English as the default Release language. See [0.11.0 validation](docs/validation-0.11.0.md) for release checks, historical decision results, live acceptance and remaining limits.

## 0.10.3 — 2026-10-21

- Add an optional manual `check-updates` command that anonymously checks the plugin's public stable release and reports versions and links without installing anything. No project mapping or account login is required; failed checks remain unknown.
- Keep project sync-bundle compatibility and connection checks in the default `plane-start` flow without querying newer plugin releases. The installed plugin's reviewed catalog still identifies sync bundles; users, installation tools or host marketplaces manage skill updates.
- Revise the English and Chinese READMEs and update guidance, removing examples that treated `npx skills check` as purely read-only. Preserve configuration, authorization, checkpoints and in-flight tasks. See [0.10.3 validation](docs/validation-0.10.3.md) for verification scope and unverified items.

## 0.10.2 — 2026-10-21

- Version the plugin and GitHub synchronization bundle independently, so skill, documentation and local-helper updates no longer require changes to project synchronization scripts.
- Identify sync bundles through complete file hashes and a config/binding compatibility catalog. Compatible older bundles remain ready, optional updates are reported separately, and unknown files or required upgrades need separate review.
- Surface update notices through existing read-only task-start/resume checks without automatically changing project configuration, authorization, tasks or scripts, or creating upgrade PRs. Version knowledge comes from the installed plugin's catalog.
- Preserve the current 0.10.1 business sync bundle byte for byte; no project migration is required. See [0.10.2 validation](docs/validation-0.10.2.md) for added regressions, release validation and unverified items.

## 0.10.1 — 2026-10-21

- Fix missed successful `pull_request_target` events in `check-github`: GitHub's reported PR branch/commit is no longer incorrectly required to match the default branch for connection verification.
- Continue checking the current default branch, commit, latest run result and Secret update time. Other event types and failed or incomplete PR runs do not count as successful events.
- Add regression tests and read-only rechecks of existing real PR runs. Observing an event does not prove a successful Plane write or establish the configuration version used by that event; comments and state require independent verification.
- Update only the plugin and standalone skill packages, preserving configuration, authorization and in-flight tasks. Copied synchronization files in business repositories do not update automatically. See [0.10.1 validation](docs/validation-0.10.1.md) for scope, historical run windows and unverified items.

## 0.10.0 — 2026-10-21

- Rename the project to **Plane DevFlow**, updating repository references, plugin and marketplace identities, npm package and command, configuration file, task-record directories, sync files and PR/comment markers.
- Retain the three skill names `plane-setup`, `plane-start` and `plane-deliver`; change the plugin invocation prefix to `$plane-devflow:`. Runtime identifiers use the new name exclusively, without old-name aliases or fallback logic.
- Use `0.10.0` to mark the runtime/configuration migration boundary. Historical tags and Releases retain their original names and remain intact. Old business configuration, task records, sync files and PR markers do not migrate automatically; see [upgrade boundaries](docs/installation.md#upgrade-from-the-previous-name).
- Isolate native-client tests with an environment-variable allowlist, empty credential files and macOS Keychain/Mach service restrictions. Verify isolation before startup so tests cannot use real account authorization.
- GitHub/Skills CLI distribution requires no project-owned npm package. This release does not publish the `plane-devflow` npm package or change business repositories or account authorization. See [0.10.0 validation](docs/validation-0.10.0.md) for results and unverified items.

## 0.9.1 — 2026-10-20

- Default recommended installation to project scope by removing `--global`; users can add it when needed. Update installation, update and removal examples in both READMEs and compatibility guidance. Existing global installations, configuration and authorization do not migrate automatically.
- Retain `plane-setup`, `plane-start` and `plane-deliver` as separate entrypoints and recommend installing the complete workflow together. Explain each stage and how each repository runs setup independently and stores its own Plane project mapping.
- Revise documentation and publication checks without changing skill behavior, MCP configuration, mapping format or authorization boundaries. Clarify that small fixes normally increment the patch version; wording changes do not require a minor release.
- See [0.9.1 validation](docs/validation-0.9.1.md) for scope and unverified items. Existing limits, including fresh-client OAuth, Cursor native skill loading and real business end-to-end workflows, remain.

## 0.9.0 — 2026-10-20

- Default installation to `npx skills add SoaringLabs/plane-for-codex --skill plane-setup plane-start plane-deliver --global`; select Codex, Claude Code, Cursor or OpenCode interactively or with `--agent`. Standard distribution requires no project-owned npm publication.
- Bundle runtime scripts, complete references and fallback guides for the other entrypoints into each skill. Support user-scope, project-scope and individual-skill installation; validate resource references and generated-output drift.
- Add shared host-capability checks and four invocation/MCP guides. Distinguish skill installation, MCP configuration, model login, Plane OAuth and actual tool access, using each host's native invocation conventions.
- Preserve the complete Codex plugin, qualified skill identifiers, configuration format, task records, synchronization and authorization boundaries. Existing local plugins keep their selected source and do not automatically migrate to standalone skills. The legacy npm 0.8.1 installer remains a compatibility channel; no new npm publication is made.
- Verify isolated global/project installation of all three skills, repeated installation, runtime scripts and configuration preservation after removal across all four agents. Codex, Claude Code and OpenCode native discovery passed; Cursor native skill loading remains unverified because client login is required.
- Reading MCP configuration does not prove authorized access. Public-source Cursor checks returned connection failure twice; retain that limitation. Fresh-client Plane OAuth, model-driven business workflows, real PR/state writeback, Cursor GUI and remote/cloud execution remain unverified. See [0.9.0 validation](docs/validation-0.9.0.md) for cross-platform CI and final public-installation results; file installation does not substitute for end-to-end validation.

## 0.8.1 — 2026-10-20

- Standardize skill display names as `Set Up Plane`, `Start Plane Task` and `Deliver Plane Task`, with English card descriptions and default invocation prompts. Preserve existing skill identifiers and behavior.
- Add the `npx plane-for-codex@latest` installer, bundling the complete plugin, retaining a persistent source and installing through Codex's native mechanism. Verify every file and all three skills while preserving existing registrations, development directories and account authorization.
- Support repeated installation, version updates and `--check`; add retry coverage, installation locking and protection against overwriting managed files.
- Lead the README with npx installation while retaining advanced Git marketplace and development-directory instructions.

## 0.8.0 — 2026-10-20

- Make English the default README and provide a complete Simplified Chinese version with links between them. Add the product logo, live repository badges and workflow diagram, making installation and first use easier to find.
- Install through Codex's native Git marketplace with one copyable registration/install command. Document migration from old local sources, updates and removal without adding an npm bootstrap dependency.
- Reorganize the setup, task-start and delivery skill entrypoints by request type, loading detailed delivery and completion procedures on demand. Preserve existing features, authorization boundaries and synchronization ownership.
- Add 24 skill scenarios, fresh-session decision evaluations, scoring rubrics and regression tests. Validate YAML, the skill inventory, resource references, anchors and installation identity; PyYAML remains a development-only dependency.
- Prepare an acceptance environment from the task workspace on request after delivery, checking the actual task version, entrypoint and availability. Confirm PR delivery, environment readiness, human acceptance and merge authorization separately.
- Update the plugin icon and SoaringLabs developer metadata. Plugin updates preserve project configuration and authorization; copied Actions files in business repositories still require separate review before upgrading.

See [0.8.0 release validation](docs/validation-0.8.0.md), [skill evaluation](docs/validation-skill-quality.md) and [README/installation validation](docs/validation-readme.md) for scope and limitations.

## 0.7.0 — 2026-10-19

- Default new tasks in concurrent chats for the same project to separate worktrees and task branches from the freshly fetched configured base. Resume the original task in its recorded directory without switching branches in the primary checkout or another task.
- Support explicit preparation of Codex-managed worktree directories. Use the actual task directory for every subsequent file and terminal operation; creating a directory alone does not relocate later operations.
- Add `sync-task` to merge the latest base into the current task branch. Keep conflicts in that directory, resolve and commit them, revalidate and update the existing PR before merging.
- Preserve the original starting point in file-scope checks while excluding unrelated files brought in through base merges. Check the live PR base and task commit before merging; base changes, unresolved conflicts and stale evidence block the merge.
- Continue checking acceptance, merge authorization, Plane synchronization and completion handoff separately. Completing one task leaves other tasks' directories, branches and uncommitted changes intact.

See [0.7.0 validation](docs/validation-0.7.0.md) for scope and limitations.

## 0.6.1 — 2026-10-19

- Route new-requirement discussion, research and planning in mapped repositories through the task-start entrypoint. Establish task ownership before creating the first repository artifact; keep discussion-only output in chat or outside the repository by default.
- Add read-only `write-context` checks for the explicitly selected task, directory, branch, accumulated changes and planned write paths. Planning documents that do not exist yet must also fall within the authorized scope.
- Prepare new task branches from the refreshed configured base; preserve the original baseline and scope when resuming. Saving documents alone does not start implementation or trigger development-state transitions.
- Retain existing isolation, acceptance and completion rules. This release adds neither multi-task parallel orchestration nor a global file-write interceptor. See [0.6.1 validation](docs/validation-0.6.1.md).

## 0.6.0 — 2026-10-13

- Record the task directory, branch and base commit during `prepare`. Add `task-context` to set authorized file scope and check accumulated committed, staged, unstaged and untracked changes.
- Block implementation, review and merge checks on branch/directory drift, out-of-scope changes or tasks already integrated into the base branch. Draft PRs must pass the same context checks.
- Add `finish-task`: after verifying task completion and PR merge, update the primary checkout to the latest base with `--ff-only`, checking merge ancestry and local/remote alignment.
- Preserve uncommitted changes, local-only commits and other worktrees during completion checks. Save a separate continuation checkpoint on failure and retry only local handoff without changing task completion state.
- Limit this iteration to task-context guards and completion handoff; requirement capture, design previews, custom state rules and background services are outside scope. See [0.6.0 validation](docs/validation-0.6.0.md).

## 0.5.0 — 2026-10-12

- Establish goals, scope, key scenarios and acceptance criteria before starting a task. Confirm visual/interaction designs when needed and reuse existing explicit authorization.
- Add `task-progress`, storing task records, history and environment ownership in shared Git metadata with digest checks, atomic updates, interruption recovery and repeat-operation protection.
- Add `check-task`, with separate implementation, acceptance, merge and completion checks. Bind verification and human confirmation to the requirement version and commit; changes invalidate old evidence.
- Require current checks and report evidence for formal delivery. Incomplete work can be delivered as a Draft; existing Drafts do not automatically become ready for review.
- Generate current reports from task records, distinguishing partial acceptance, unverified items, background synchronization and application verification. Record human acceptance and merge authorization separately.
- Check the live PR, fresh Plane state/labels, required validation, writeback and environment cleanup before completion. Preserve existing configuration formats, completion policies and synchronization ownership; no custom state rules are added.
- Stop background merge wording from asserting that the user has not yet accepted the work. Copied scripts in business repositories require separate review before upgrading.

See [0.5.0 validation](docs/validation-0.5.0.md) for results and limitations.

## 0.4.2 — 2026-10-11

- Detect available tools before setup, supporting browser/app navigation, opening pages only and manual links. The Plane desktop app is not required.
- Add `setup-capabilities` and `setup-progress` to inspect capabilities, refresh service evidence and store non-sensitive setup progress in Git metadata.
- Support staged setup and cross-session recovery. Historical success is not current validation; an unreadable Secret does not immediately require a replacement token.
- Provide stage-specific recovery guidance for permission, login, rate-limit, network and invalid-response failures. Native mode skips runner credentials; configuration changes retain progress and trigger rechecks.
- Reconcile uncertain server-side write outcomes before retrying; do not automatically replay POST/PATCH/DELETE requests.
- 2026-10-12 compatibility fix: parse GitHub UTC timestamps on Python 3.10 while continuing to reject missing timezones and invalid time metadata.

See [0.4.2 validation](docs/validation-0.4.2.md) for results and limitations.

## 0.4.1 — 2026-10-10

- When the Actions Secret is missing, guide users through separate stages: **create a PAT in Plane → save it as the current repository's GitHub Secret → confirm the Secret name → activate and check the connection**.
- Help open pages and navigate forms when browser/computer-use tools are available; otherwise provide the complete path and repository-specific links.
- The user generates, copies, pastes and saves the PAT directly; it never passes through chat or agent clipboard reads. Keep merge authorization separate from credential-stage confirmation.

See [0.4.1 validation](docs/validation-0.4.1.md) for results and limitations.

## 0.4.0 — 2026-10-10

- Add `sync.provider` with `actions` (default) and `native`, verifying the selected mode against actual readiness evidence.
- Add `sync.api_version`, defaulting to `v1` and using `v2` separately for comment upserts. When v2 is explicitly selected, state and label safety checks still use fresh v1 reads.
- Preserve configuration formats version 1/2 and the PR binding protocol. Unknown or unparseable states and acceptance labels block writes; longer Retry-After values are not shortened to retry early.
- Support reviewed, digest-checked and backed-up upgrades of copied synchronization files in business repositories. Each repository configures its own `PLANE_API_KEY`; connection checks and actual PR writeback are reported separately.

See [0.4.0 validation](docs/validation-0.4.0.md) for results and limitations.
