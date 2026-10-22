# Unified-upgrade candidate code review

Date: 2026-10-22. Reviewed the complete implementation diff from `6600ab8` to candidate `25e8a70`, followed by review of the fixes. Scope is the mother repository, disposable test repositories and isolated installation profiles. No source push, PR, merge, release, stable promotion or business-project migration was performed.

The review used independent Standards and Spec passes, plus focused recovery and trusted-source inspection. Canonical helpers, Action inputs, setup/readiness behavior, metadata generation, installation adapters, tests and documentation were inspected. Generated standalone copies were regenerated and checked rather than edited independently.

## Standards

The governing rules are [CONTRIBUTING.md](../CONTRIBUTING.md): preserve unrelated work, read/plan versus apply behavior, idempotency, original installation ownership and accurate evidence. No additional actionable style-smell findings were retained.

| Finding | Original failure | Correction and evidence |
| --- | --- | --- |
| **P1: Host files and installation scope were not protected** | A valid canonical `.agents` payload hid a customized host copy. Actual Skills CLI 1.7.4 deleted a synthetic file in a custom Claude skill directory. A later session could also inherit a different global home/state/configuration destination. | Snapshot host copies/links, reject custom payloads and redirects, recheck drift before installation, and bind the global environment before invoking the CLI. Isolated tests prove other-scope files remain intact and installation is not invoked on drift. |
| **P2: Lockfile ownership was too broad** | An upgrade PR accepted all `skills-lock.json` edits, including another skill's source. The project lock writer discarded unknown metadata. | Bind original lock metadata; permit only product entries in PRs; preserve unrelated entries/metadata during installation; validate the actual global lock format and location. A PR regression stops before `gh` or push. |
| **P2: Local verification ignored the active host copy** | Canonical files could match the target while the selected host's active copy had been modified. | Re-read selected host contents and report `changed_after_verification`. Separate fixtures cover known copies, valid links, broken redirects and unrelated host edits. |

Standards result: **3 confirmed defects, all fixed**. The most severe was loss of customized host files.

## Spec

The source is the approved [unified release and sync plan](unified-release-and-sync-plan.zh-CN.md), stages A–E. Stage F and publication remain excluded.

| Finding | Requirement and original failure | Correction and evidence |
| --- | --- | --- |
| **P1: Legacy deletion ignored other callers/listeners** | Sections 7.1–7.2 require a single listener and removal only of recognized scripts without other callers. Another workflow survived migration while its referenced script was deleted. | Preflight additional workflows and executable/configuration callers; recheck before writing. Extra public Actions, historical listeners, workflow callers, non-workflow launchers and post-plan additions stop migration. Unrelated workflows and documentation remain allowed. |
| **P1: Native projects could falsely complete** | Sections 6.2 and 9 require activation independently of local installation. A native mapping check plus a local refresh yielded `candidate_complete` while the remote tracked skills remained old. | Verify target tracked payload fingerprints on the activation branch for native and Actions projects. Local payloads and green mapping/connection evidence cannot substitute for remote deployment. |
| **P2: Emitted candidate manifests could not exercise upgrades** | Sections 6.2 and 8 specify an explicit candidate test channel. The generated `channel=candidate` manifest was rejected; earlier tests used stable-labeled synthetic manifests. | Bind explicit candidate selection into the plan, expose isolated-source CLI arguments, verify that channel throughout staging, and retain `candidate_fixture`/`candidate_complete`. Real Skills CLI coordinator tests now consume candidate manifests in both scopes. |
| **P2: Interrupted source/backup copies could become permanent blockers** | Section 6.4 requires independent retryable steps. A partial final directory was treated as a completed copy and failed every retry. | Copy into temporary sibling directories, verify every byte and publish the directory only after success. Fault-injection regressions retry source copying and installation backup without overwriting unknown content. |
| **P2: Worktree creation had an ambiguous-result window** | Section 6.4 requires reconciliation after interruption. A successful Git worktree operation whose response was lost left no record and failed on retry. | Persist intended identity before Git changes, reconcile the exact path/branch/base, and reject moved checkouts. A timeout injected after the actual Git operation resumes the same worktree. |
| **P2: Rollback readiness was recorded before restoration** | Section 7.3 requires a verified reverse diff that preserves later changes. A failed restore followed by retry returned the saved directory without producing the reverse diff. | Record `preparing` versus `diff_prepared`; retry restoration only from known original/target bytes; verify the reverse files and preserve edits made afterward. No reset, merge or local downgrade is performed. |
| **P2: Plugin handoff was tied to the old installation path** | Section 6.3 requires resuming through the original channel after host refresh. A host can activate a new versioned directory while the saved plan continues to inspect the previous directory. | Explicit confirmation accepts the resolved active plugin root, verifies its complete payload and records it independently of the immutable original plan. A fixture retains both old/new directories, preserves the old bytes and detects later edits to the confirmed target. No real host update was performed. |

Spec result: **7 confirmed defects, all fixed**. The most severe issues were deletion of still-used scripts and false remote activation.

An additional Section 6.3 contract was hardened: the CLI now verifies and delegates post-staging commands to the staged helper in a fresh process. This prevents self-update coordination from lazily importing replacement modules from the active installation. A regression checks exact delegation, same-helper termination and rejection of tampered staged code. A separate real subprocess smoke check executes the delegated status command successfully. No current-version mixed-module failure was claimed or reproduced.

## Verification and retained failures

The [candidate validation](validation-0.14.0.md) retains the original implementation baseline separately. Final review verification:

| Check | Observed result |
| --- | --- |
| Full Python suite in the development environment | **500 passed** in 315.022 seconds |
| Final plugin-handoff metadata/path guard | Targeted regression passed, including refusal before scanning an unrelated directory |
| Node installer/credential unit suite | **23 passed** |
| Actual Skills CLI 1.7.4 | Project/global coordinator installation from explicit candidate manifests passed; selected/fixed-commit/repeat/removal/native Codex checks passed |
| Actual npm plugin integration | 53 packed files / 46 plugin files; fresh/repeated/check/retained-source/native Codex discovery passed |
| Four-host file/helper matrix | Project/global/repeat/removal and configuration preservation passed; only Codex native discovery/configuration executed |
| Original real-profile metadata protection | Unchanged in all actual installation suites |
| Version and standalone generators | `--check` passed; no drift |
| Package/resources | Canonical and generated payloads, reachable links/anchors and inventory passed |
| Decision/execution corpora | 48 / 5 structurally valid; no new model execution |
| Offline demo, staged CLI subprocess, whitespace and scope audit | Passed |

The initial source-copy regression failed against the original implementation, reproducing the non-retryable partial directory. The first actual global coordinator installation exposed a legitimate upstream lock default (`dismissed: {}`) that the new guard rejected; the guard now accepts that exact initial default and still rejects unrelated changes. The initial broad Python command ran 455 tests with three module-import errors because its system interpreter lacked the development-only PyYAML dependency. A subsequent pinned-development-environment run passed 499 tests before the final plugin-path regression was added; the final complete run passed 500. These failed attempts are retained as test/environment evidence, rather than reported as passing runs.

Installation probes use disposable state and credential isolation. No real profile, OAuth, PAT or business mapping is copied into fixtures. Structural corpus validation and deterministic harness tests are not new model-driven assessments. Existing synthetic model-usage-limit messages in harness tests are fixture output, not live model sessions.

## Remaining boundaries

- The candidate is unpublished. Public stable installation, actual formal release-asset delivery, remote CI and a real GitHub run of the new public Action remain unverified.
- No actual project migration/upgrade PR, activation dispatch, production event writeback or production rollback was performed.
- Native skill discovery was exercised for Codex. The other host matrix results cover files/helpers; their native clients and OAuth/model sessions remain unverified.
- Extra-listener/caller detection is a conservative source preflight, not whole-program analysis. Dynamically constructed script paths and externally managed listeners still require the pre-merge inventory and queue review described in the operator workflow.
- Hard process termination may leave a process lock or an abandoned temporary directory. The operator must inspect ownership before removing a stale lock; the tool does not remove a live updater's lock automatically.

These limits preserve the planned sequence: review, separately authorize remote verification/publication, then authorize individual business-project migration.
