# Plane DevFlow 0.10.2 validation

Plugin 0.10.2 separates its release version from GitHub sync bundle 0.10.1. The three standalone skills follow the plugin version. Both runtime scripts and the generated workflow remain byte-for-byte identical to sync bundle 0.10.1; existing project mappings, credentials, authorization and task records require no migration or version-only upgrade PR.

## Behavior

The installed catalog recognizes complete fingerprints for sync bundles 0.10.0 and 0.10.1, config schemas 1/2 and PR binding protocol 1. A supported older bundle remains ready with an optional maintenance notice. Unknown/customized files need review; explicitly incompatible versions require a reviewed upgrade. Normal task-start/resume checks surface these distinctions through the existing read-only setup-progress flow. They do not change scripts, create PRs, merge, reconnect accounts or write Plane work items. Persisted setup checkpoints keep their existing schema for older installed sessions; fresh remote evidence is still required.

The latest-known bundle comes from the installed plugin catalog, rather than a background service or live upstream version API. Updating the plugin refreshes the catalog. Exact default-branch connection checks, Secret freshness, manual completion and task authorization boundaries remain in force.

## Verification

The [pre-release candidate record](validation-sync-bundle-compatibility.md) preserves the original regression failure and candidate evidence. The release candidate passed 280 Python tests, 23 npm tests, generated distribution drift, resource/package validation across 66 Markdown files, 27 eval-corpus structure cases and the offline demo. Actual tarball/native Codex installation and Skills CLI checks compare the complete payload and exercise all three skills with isolated credential stores. Final release, public-source installation, CI and local-install readbacks are recorded in the GitHub Release after publication.

An existing business repository's current-main read-only connection workflow succeeded separately from package tests, matched the inspected default SHA and reported no writes. Fresh helper readbacks reported both inspected business repositories ready, with intact and compatible 0.10.1 bundles. This is a connection check, not new PR-event writeback verification. The sync bundle remains 0.10.1 in existing business repositories; matching plugin and runtime version numbers are no longer required.

## Limits

- Corpus structure checks and helper regressions do not establish fresh model-driven decision quality. Fresh model evaluations and new OAuth flows are not performed.
- Native discovery and MCP configuration readback were verified for Codex, Claude Code and OpenCode in isolated profiles. Cursor native skill discovery remains unverified because client login is required; configuration readback does not prove authenticated Plane access.
- The four-host local checks run on macOS. Cross-platform Python/installer/Skills CI is separate from native GUI or end-to-end business flows on every platform.
- No new real PR, task/comment mutation, npm publication or business synchronization script upgrade is part of this release. Existing authorization is reused without copying credentials into test profiles.
