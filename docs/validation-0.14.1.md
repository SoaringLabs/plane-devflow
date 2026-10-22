# 0.14.1 rate-limit reliability validation

This is an unpublished patch candidate. It changes local product release resolution and verification reporting; it does not migrate consuming repositories, merge a PR, create a tag, publish a Release, promote `stable`, or replace an installed plugin.

## Behavior and regression scope

- Existing GitHub CLI authentication supplies canonical Release metadata reads. Missing/unconfigured CLI can use anonymous public reads; authentication, SSO/permission, missing resources, network failures and invalid responses retain separate safe errors. Token values are never extracted or stored by the helper.
- A successful pinned-version resolution caches public version/commit/asset/manifest identity for one hour across local repositories. Corrupt, expired, future-dated, mismatched and symlinked cache records cannot supply identity. Cache storage failures leave live reads available.
- Explicit release selection and final upgrade verification bypass the identity cache. A moved tag or unavailable remote identity cannot be accepted using earlier success. Latest-release selection remains live.
- Primary and secondary rate limits retain their stage and UTC retry time. Transport-specific cooldowns suppress repeated release requests until retry is permitted; no automatic retry job is installed.
- Connection and activation observations remain available when release identity is unverified. Overall upgrade completion still requires every existing gate. Event writeback remains a separate unverified result.
- Full product version metadata and all three generated standalone distributions use 0.14.1. Historical bundle bytes and compatibility entries remain unchanged. Existing 0.14.0 Action pins remain compatible; this patch does not require a project workflow change just to benefit from the local resolver fix.

## Executed evidence

Focused transport/cache regression tests cover authentication reuse and fallback boundaries, error classification, primary/secondary cooldowns, explicit refresh, changed tags, source validation, cache failure modes and public asset redirect restrictions. Upgrade regressions cover successful connection with pending identity verification and mandatory fresh final acceptance.

A read-only check against the published 0.14.0 Release resolved its actual annotated tag to `bc30810c5fdf465e8c6933d47235d56a695460ab` and validated the 313-file manifest. The first resolution made three authenticated metadata requests and one public manifest download; a repeated pinned-version resolution made zero metadata requests and returned the same manifest. Evidence was captured with a disposable public-metadata cache, without modifying any business repository or credential.

Local checks completed on macOS with Python 3.14 and Node.js 24:

- Full Python suite: 519 tests passed. The initial system-interpreter invocation could not import three test modules because PyYAML was absent; that failure was retained. A disposable virtual environment with the pinned development dependency passed the complete suite.
- Node installer/credential-isolation suite: 23 tests passed.
- Actual npm tarball/npx installation, repeated installation and native Codex discovery passed with disposable profiles; protected original profile metadata remained unchanged. The final payload was checked again after the cache storage guard was adjusted.
- Skills CLI project/global installation, repeated installation, payload/helper checks and removal passed for Codex, Claude Code, Cursor and OpenCode. Codex native discovery/configuration passed; native/model/OAuth execution on the other hosts was not claimed.
- Version generation, standalone generation, package validation, 48 decision-case definitions, five execution-case definitions, offline demo and `git diff --check` passed. The npm dry-run inventory contained 55 files and excluded development/private artifacts.

The candidate PR's exact-head checks provide the remote Python 3.10/3.14 and macOS/Linux/Windows installation evidence separately from these local results.

## Limits

Synthetic HTTP errors exercise quota behavior without deliberately exhausting a real account. The live read proves current public-release resolution and cache reuse, not a new 0.14.1 publication or business lifecycle writeback. Fresh model decision/execution sessions are not required for this local transport patch and were not run. Cross-platform integration is assessed by the PR's CI matrix. Historical staged upgrade helpers retain their original pinned implementation; installing this patch does not rewrite existing upgrade plans or their staged sources.
