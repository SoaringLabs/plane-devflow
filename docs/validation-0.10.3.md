# Plane DevFlow 0.10.3 validation

Plugin 0.10.3 adds an optional manual update check. Its three standalone skills share that plugin version; sync bundle 0.10.1, the runtime scripts, workflow and compatibility catalog remain byte-for-byte unchanged. Existing mappings, account authorization, setup checkpoints and in-flight tasks need no migration or version-only business PR.

## Behavior

Ordinary `plane-start` and `setup-progress` retain their existing project synchronization and bundle compatibility checks without querying the plugin release API. Plugin updates remain an explicit user, installer or marketplace action. No background updater or automatic installation is added.

On an explicit request, `plane_workflow.py check-updates` anonymously reads the canonical public stable Release and reports installed/latest versions and an advisory link. It works outside a repository without Git, GitHub CLI or account login. A three-second worker deadline covers DNS and response reads; a quota failure permits one canonical latest-link HEAD inspection within that budget. Remote prose/assets are ignored, redirects are not followed and no project/task/checkpoint files or trusted bundle catalog are written. Offline, failed and invalid checks leave the version unknown and exit without blocking task work; unknown does not mean no update exists.

README and installation guidance describe this manual entry and explicit installation/update commands. They no longer present `npx skills check` as guaranteed read-only. A newer plugin alone does not require updating business synchronization scripts.

## Verification

The [historical unpublished candidate record](validation-plugin-update-check.md) preserves the manual-only scope and original regression evidence on plugin 0.10.2. The 0.10.3 release payload passed 304 Python tests (24 added regressions), 23 npm tests, generated-skill drift and package/resource validation across 68 Markdown files, 31 eval-corpus structure cases and the offline demo. Actual tarball/native Codex installation verified 37 packed files / 31 plugin files and all three enabled skills, fresh/repeat/check behavior, cache removal and retained local sources. Skills CLI 1.7.4 and four-agent checks passed project/global/repeated installation, payload/helper comparisons and removal with configuration retention. Codex, Claude Code and OpenCode native discovery/MCP configuration readback passed; Cursor configuration readback passed with the native-discovery limit below. Final public-source installation, source/tag CI and local plugin update readbacks are recorded in the GitHub Release after they complete.

Regression coverage includes anonymous fixed-source requests, stable version and link validation, API-quota fallback, untrusted prose/assets, bounded responses, HTTP/network failures, stalled-process termination, repository/account independence and offline behavior. Daily Actions/native progress is guarded against calling the plugin checker. Existing checkpoint interoperability, sync compatibility and preservation checks remain in place.

Isolation uses empty credential stores and native credential-access restrictions. Complete installed payloads and all three skills are compared with reviewed source. Real profile configuration bytes, credential metadata, business mappings and task/checkpoint records are checked separately; unrelated or concurrent task changes are preserved.

## Limits

- Manual release discovery detects GitHub's designated stable Release, not unreleased commits, per-skill folder changes or prereleases. Anonymous network/rate-limit failures can leave the result unknown. It does not refresh the installed sync compatibility catalog.
- Corpus validation and helper regressions do not establish fresh model-driven decision quality. Fresh model evaluations, new OAuth flows and new real PR/comment/status writeback are not performed.
- Cursor native skill discovery remains unverified because client login is required. MCP configuration readback is separate from authenticated Plane access.
- Local native checks for Claude Code, Cursor and OpenCode run on macOS. Windows/Linux native loading for those clients, GUI/cloud business flows and end-to-end behavior on every platform remain unverified. Cross-platform package CI is reported separately.
- Skills CLI installation, reinstallation, removal and payload checks do not verify its automatic update tracking.
- No Plane-owned npm publication, business sync script upgrade, account reauthorization or Plane task mutation is part of this release.
