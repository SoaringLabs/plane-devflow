# Sync bundle compatibility candidate validation

This is an unpublished candidate based on plugin 0.10.1. It separates the plugin release identity from the copied GitHub sync bundle and reports maintenance notices through the existing read-only `setup-progress` step used when starting/resuming a task. Neither a public release nor an update to the real installed plugin is performed.

## Behavior and integrity

The trusted installed catalog recognizes the exact workflow and both runtime script hashes for sync bundles 0.10.0 and 0.10.1. Both support config schemas 1/2 and binding protocol 1. A compatible older bundle stays ready and receives an optional update notice; unknown/modified files remain unrecognized, and releases explicitly requiring an upgrade fail compatibility. Optional maintenance does not create a PR or authorize changes. GitHub runtime source/workflow bytes remain identical to the published 0.10.1 bundle.

Plugin version metadata is separate from `plane_sync.VERSION`. A synthetic plugin version advance is tested without changing any sync bytes. Release validation rejects runtime or generated workflow drift against the reviewed bundle catalog. Three standalone skill distributions retain their plugin version and report the independently packaged sync version.

## Checks

The original helper first failed the regression where an exact supported 0.10.0 bundle should remain ready. New tests cover trusted full fingerprints, config/binding compatibility, required upgrades, optional updates, customized files, incomplete reads, legacy checkpoints, daily routing and preservation of mapping/task files. Exact-head/current-default-branch connection verification and Secret freshness checks remain unchanged.

The final candidate passed **280 Python tests** (13 added regressions), **23 npm installer/credential-isolation tests**, generated-source drift checks, package/resources across **65 Markdown files**, **27 eval-corpus structure cases** (three added scenarios) and the offline demo. The plugin source fingerprint remained unchanged during the final verification run.

Actual local-tarball installation compared all **30 plugin files** (36 files in the tarball), loaded all three native Codex skills, and verified repeat/check/source-retention behavior. Skills CLI 1.7.4 passed project/global and individual skill installation, exact payload/helper startup, repetition and removal preserving synthetic configuration/authorization. The four-host matrix passed for Codex, Claude Code, Cursor and OpenCode. Native discovery and MCP configuration readback passed for Codex, Claude Code and OpenCode; Cursor configuration readback passed while native discovery remained blocked by client login. All installation checks used isolated profiles and retained protected real-profile metadata.

Read-only checks of two existing business repositories both identified their untouched 0.10.1 bundles as current, intact and compatible. One repository was ready. The other had a newer default-branch commit without its matching connection-check run; both the installed baseline and candidate reported the same unverified connection at the same SHA. This is not a bundle-version regression. No remote dispatch or task write was performed to clear that status.

Primary checkouts, business mappings and protected authorization/settings metadata were unchanged by the candidate work. Concurrent activity updated two task/checkout records in one business repository; those changes were observed and left intact, rather than overwritten with the preservation snapshot. Old and newly saved setup checkpoints retain legacy-format interoperability. Raw local evidence is private and excluded from this checkout.

## Limits

- `latest_known_version` is the latest sync release in the installed plugin catalog. This is not a background monitor or a live upstream-latest API; update the installed plugin to refresh that catalog.
- This candidate does not upgrade business repositories, refresh the user's installed plugin or publish source, a tag, GitHub Release or npm package.
- Fresh OAuth and model-driven decision quality are separate from helper regression tests, corpus validation and isolated native skill discovery. No new real PR writeback or Plane mutation is needed or claimed for this change.
