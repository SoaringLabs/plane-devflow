# 0.4.0 validation

2026-10-10. This release implements `sync.provider` (`actions` default, `native` optional) and `sync.api_version` (`v1` default, `v2` optional) without changing mapping schema versions 1/2 or PR binding protocol 1.

## Checks performed for this release

- `python3 -m unittest discover -s tests -q`: 99 tests passed.
- HTTP integration tests run a real loopback HTTP server with controlled Plane-shaped responses. They exercise v1 task/state reads and writes, v2 comment upsert replay, unexpanded UUID state/label resolution, terminal protection, acceptance-label protection, and explicit v2 writes guarded by fresh v1 relation reads. These are local contract tests, not live Plane calls.
- Isolated Git tests verify mode selection/reconfiguration, legacy byte preservation, clearing old state targets on project changes while retaining provider preference, exact-config native receipts, no native Actions/Secret inspection, reviewed script upgrades, backups, and rejection after a stale manifest.
- Existing regression coverage verifies GitHub event bindings, current PR snapshots, lifecycle retries, basic mappings, state-target connection reads, stale connection runs, Secret replacement, worktree isolation and delivery behavior. Native Actions execution skips before constructing a Plane client; native connection dispatch cannot claim an Actions PAT verification.
- Long Retry-After is rejected for a later run instead of shortened to an early retry.
- `scripts/validate_package.py`, all three Skill creator validators, Skill UI YAML and generated/composite workflow YAML pass. Skill validation uses a temporary Python environment with PyYAML; runtime scripts remain standard library only.
- The isolated offline demo completes branch creation/resume, linked delivery planning, review/merge/manual acceptance and one stable lifecycle comment. No live services are called by the demo.

## Evidence limits

This release did not provision another Plane project or recreate the cleaned-up runner Secret. Prior live Free-account API and Actions capability results are recorded separately in [capability verification](plane-github-capability-verification.md); they are not a fresh execution of the 0.4.0 runner. Official v1 identifier routing is documented in [Plane's v1 API reference](https://developers.plane.so/api-reference/issue/get-issue-sequence-id).

Native provider configuration and suppression of overlapping plugin writes are tested. A paid account's official GitHub integration was not exercised end to end. Native readiness requires actual UI observation or explicit user confirmation of repository/project mapping, workflow rules and disabled overlapping Actions. Its receipt includes provenance and observation time and binds the exact configuration. It is not automatic integration discovery or proof of a real PR event write.

Business repositories need a reviewed bundled-script upgrade and their own runner credential. Full Actions readiness still requires trusted files/config in the default branch and a fresh connection run; actual PR writeback is reported separately. Fork/Dependabot behavior, reverse webhook synchronization and multiple repositories writing one task remain outside this release's live verification.

## Local installation

`codex plugin add plane-for-codex@plane-for-codex --json` installed **0.4.0** in the local plugin cache. Installed inventory confirms it is enabled. All 14 package source files match the installed cache by SHA-256; the installed CLI reports 0.4.0. The official MCP server name/URL remain unchanged.

The installed `doctor` was run read-only against an existing business repository: existing project mapping remains valid, completion policy remains manual, provider resolves to Actions and API routing to v1. The repository's working tree remains clean on its existing setup branch. Its copied synchronization files require the reviewed upgrade during resumed initialization; local plugin installation does not activate or modify that business workflow.
