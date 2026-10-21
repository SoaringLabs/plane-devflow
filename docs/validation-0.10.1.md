# 0.10.1 release validation

This patch corrects the auxiliary `check-github` report for successful `pull_request_target` runs. GitHub can report the PR head branch and commit even when the workflow checks out a trusted default-branch commit. Event observation now examines the repository's synchronization workflow runs without applying the connection check's default-head filter. Connection verification still requires the current default branch and commit, the latest matching dispatch result, and a run newer than the runner Secret metadata.

## Regression and release checks

The new regression first reproduced the false negative on the unchanged helper. Coverage includes a successful event on a different PR head, unrelated event types, unsuccessful or unfinished PR events, and the separation between event observation and stale, failed, missing or non-default-branch connection checks. The mocked GitHub boundary accepts only the expected repository/workflow endpoint.

Release checks cover the complete Python suite, npm installer/credential-isolation tests, generated skill drift, package/resources, eval corpus structure, the offline demo, actual full-plugin installation and Skills CLI installation in isolated profiles. Final totals and source/tag CI readbacks are recorded in the [0.10.1 Release](https://github.com/SoaringLabs/plane-devflow/releases/tag/v0.10.1).

The local candidate passed 267 Python tests, 23 npm tests and all 24 eval corpus structure cases. Generated-source and package/resource checks passed. Actual tarball installation loaded all 28 plugin files and three native Codex skills. Skills CLI 1.7.4 passed all-three and individual skill installation, project/global scope, repetition, helper startup and preservation checks. All four host installation matrices passed; native skill discovery and MCP configuration readback passed for Codex, Claude Code and OpenCode. Cursor MCP configuration readback passed with `requires_authentication`, while native skill discovery remained blocked by client login. No real credentials were copied into these profiles, and protected real-profile metadata remained unchanged.

Before the version bump, read-only checks against two existing migrated repositories both reported `event_run_observed: true`, `connection_verified: true`, `github_sync: ready` and complete initialization. Their already successful real PR-target runs use PR head metadata different from the trusted base checkout. No new PR event, Plane comment or state mutation was required for this diagnostic fix. Raw run and preservation evidence remains private.

## Preservation and limits

- Event observation means at least one successful PR-target run among the latest 100 runs returned for the repository's synchronization workflow. It is historical evidence, not certification of the current checkout, current configuration, PR binding, Plane comment or state write. An unbound PR can succeed without writing anything. Connection readiness and real writeback remain separate checks.
- The plugin and its three generated standalone skills share this fix. Existing marketplace identity, skill identifiers, MCP configuration, repository mapping format and authorization boundaries are unchanged. Local plugin refresh is checked separately against the existing source and preserved configuration/authentication.
- The version bump does not update copied synchronization files in business repositories. Their 0.10.0 runtime remains installed; a 0.10.1 helper can consequently report a bundle version/hash mismatch while correctly observing the existing event and verified connection. Updating those files requires a separate reviewed repository change.
- This patch does not claim fresh OAuth completion, authenticated MCP access in fresh clients, a new real PR writeback or model-driven end-to-end acceptance. Existing Cursor login/native-discovery limits and unavailable native host sessions on other operating systems remain unverified.
- No Plane-owned npm package is published for this release; Skills CLI distribution reads the GitHub repository directly.
