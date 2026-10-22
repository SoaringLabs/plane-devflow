# 0.14.0 unified-release candidate validation

The follow-up [code review and recovery fixes](review-0.14.0.md) record the later review separately from the original implementation checks below.

2026-10-22. Mother-repository implementation only. No business repository was migrated, no real user installation was updated, and no source branch, tag, GitHub Release, npm package or stable-channel update was published.

## Implemented contracts

- `VERSION` drives plugin, npm and standalone distribution metadata. The public synchronization runtime imports the same generated product version. Historical copied bundles retain frozen bytes and fingerprints as a legacy adapter, rather than a new independent release sequence.
- The public composite Action accepts the trusted event configuration commit. New setup generates one small workflow pinned to a formal product commit, leaving project mapping and runner credentials with the consuming repository.
- Product manifests bind committed source, the public skill inventory and file fingerprints. The resolver peels annotated tags and checks the manifest against the actual commit. It does not treat a development branch or `target_commitish` string as formal release identity.
- The upgrade helper provides read-only planning, exact-plan recording, fixed source staging, isolated project preparation/PR reconciliation, original-channel installation, activation/connection verification and reverse project diffs. Its non-secret record survives installation replacement.
- Tracked project skills are upgraded in the isolated project workspace. A clean original base checkout is synchronized only after activation; busy or different branches retain their work and receive an explicit handoff. Native-provider installations do not gain an Actions listener.
- Upgrade PRs validate planned bytes, deleted files, working changes and the Git index independently. Recreated legacy scripts, customized payloads and unrelated staged files stop delivery without being overwritten. Upgrade activation uses the actual remote default branch, independently of the task development base.

The three public skills remain unchanged in identity; `plane-setup` routes scoped product upgrades to the new reference. Mapping schemas 1/2, PR binding protocol 1 and existing state/acceptance behavior are retained.

## Executed checks

Environment: macOS arm64, Python 3.14.3, Node.js 24.15.0 and actual Skills CLI 1.7.4. Installation tests used disposable profiles and credential isolation.

| Check | Observed result |
| --- | --- |
| Full Python suite | **470 passed** |
| Node installer/credential isolation unit suite | **23 passed** |
| Single-source version generation | `build_version.py --check` passed |
| Standalone generation | `build_skills.py --check` passed for all three skills |
| Package/resources | Source, generated skills, reachable resources/anchors and public inventory validation passed |
| Decision corpus | **48 cases structurally valid**; three product-upgrade routing/scope scenarios added |
| Execution corpus | **5 cases structurally valid**, with no fresh model execution |
| Offline demonstration | Passed without live services |
| Whitespace | `git diff --check` passed |

The product-specific cases exercise formal tag/manifest identity, payload/path integrity, trusted Action input, shared readiness, known legacy removal, interrupted migration restoration, exact plan/target binding, read-only plans, source and mapping drift, independent workspaces, tracked project activation, native-provider behavior, PR scope protection and reverse legacy restoration. A local bare Git fixture verifies remote-default discovery without changing local refs.

### Actual installation evidence

The local npm tarball contained **53 files**, including **46 plugin files**. Fresh/repeated installation, retained local source, source/cache removal, check mode and native discovery of all three Codex plugin skills passed.

Actual Skills CLI passed project/global installation, selected and individual skills, repetition, changed-source refresh, removal and exact payload/helper startup. A synthetic GitHub tree URL was rewritten to an isolated local Git transport: installation selected the earlier full commit even after the source branch changed. This tests real CLI ref parsing and Git behavior, not public GitHub update tracking.

The new upgrade coordinator itself installed the candidate through actual Skills CLI in both project and global disposable profiles. It verified all installed bytes and retained native-provider ownership. These runs used explicit candidate source staging and synthetic project metadata; their status remained `verification_pending`, rather than claiming production activation or writeback.

The four-host installation matrix passed project/global/repeated installation, all three payloads/helpers, preservation of synthetic configuration/authentication, and removal preserving mapping and connection settings for Codex, Claude Code, Cursor and OpenCode. Native discovery and MCP configuration readback passed for Codex. The other three native clients were not executed in this run; their discovery/configuration results remain `not_run`. Model sessions and OAuth remain unverified for all hosts.

All installation suites read back unchanged protected real-profile metadata. No real credential content was needed or copied.

## Retained failures and corrections

The first baseline run executed 430 tests and reported three failures plus one error. The failures encoded the superseded requirement that runtime/workflow edits require an independently versioned copied bundle. They were replaced by product-version/runtime consistency and committed-manifest integrity coverage. The error came from a credential-guide fixture entering public release discovery; it now supplies explicit synthetic release data instead of calling the network.

Early upgrade cases exposed missing destination-parent creation and a mapping-drift fixture that changed a value to its existing value. Parent preparation and the discriminating drift case were corrected. Later review added Git-index scope checks, exact prepared-file checks, tracked-install isolation/activation, and actual remote-default selection. The final full suite passed after those changes. Existing synthetic HTTP-error cleanup warnings are not live service failures.

## Explicit limits

- The candidate has not been published. Public stable installation, actual formal asset download, stable-branch promotion and execution of the new Action from a published GitHub commit remain unverified.
- No real project setup/migration, connection dispatch, production PR-event writeback, project upgrade PR creation/merge or production rollback was performed. Local fixtures and mocked HTTP contracts do not establish those results.
- Skills CLI public-source automatic update tracking remains unverified; it is separate from the verified fixed-commit installation and explicit unified upgrade path.
- Plugin updates retain a recoverable original-channel handoff and payload confirmation. No automatic refresh of a running real host or duplicate MCP registration was attempted.
- macOS local checks do not establish Windows/Linux native-client behavior or remote CI. The existing CI matrix and new version/generation checks are prepared but were not run remotely.
- Corpus validation and deterministic harness tests do not establish new model-driven skill decision quality. No new model assessment or business acceptance is claimed.

The rollout order remains: review this candidate, authorize publication separately, verify the public Action/release channel in an explicitly scoped test environment, then authorize individual business-project migration. See the [approved plan](unified-release-and-sync-plan.zh-CN.md), [installation guide](installation.md) and [upgrade operator reference](../plugins/plane-devflow/references/product-upgrades.md).
