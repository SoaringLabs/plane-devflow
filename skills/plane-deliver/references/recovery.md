# Capability detection and setup recovery

Read this at initialization, when resuming, or when a setup operation fails. Use `setup-capabilities` before requiring a repository or account; `bootstrap-status --repo TARGET` also inspects an absent/unmapped target and returns a portable handoff. After association use `setup-progress`. These belong to `scripts/plane_workflow.py`. New-computer preparation follows [first-project onboarding](first-project.md).

## Detect and choose assistance

`setup-capabilities` detects local Git and GitHub CLI executables. Host UI capabilities cannot be inferred from installed apps: inspect the current tool inventory and pass repeated `--surface browser-control`, `--surface app-control` or `--surface url-opener` only for available tools. These flags report host capabilities, not authentication or permission grants. Tool refusal/disconnection changes the available route; remove the unusable surface and continue with the next available route. No surfaces defaults to manual clickable links. A Plane desktop installation is optional; use the configured Plane web origin when absent. Discover an authenticated session separately; a working MCP connection does not prove that a browser is logged in.

Before association, missing Git/repository/Plane authentication is a prerequisite to resolve, not permission to install apps, register accounts, upgrade plans or create replacement projects. Explain the current missing prerequisite and preserve successful authorization. This release's Git helper supports github.com only; GitHub Enterprise remotes need a supported adapter and must remain partial, without constructing github.com credential destinations for them. Self-hosted Plane uses the configured origins; verify account/API access and GitHub Runner network reachability rather than assuming the Cloud endpoints or bundled Cloud MCP can access that instance.

## Resume after association

Run `setup-progress --repo /absolute/repo --apply` to refresh remote evidence and persist a non-secret checkpoint. Add observed surfaces. It performs Git/GitHub reads and a local write under the Git common directory, never a service mutation. Check-only requests omit `--apply`. `--offline` is useful for local inspection but leaves Actions remote checks unknown. Missing gh permits manual credential storage, while automated verification remains pending; an available authorized GitHub connector may supply separately reported evidence, but does not turn the helper's unknown result into verified readiness.

Checkpoints are keyed by the entire validated configuration digest. Worktrees with the same mapping share progress; changed provider/project/rules/API routing uses another checkpoint and preserves the original. A new machine reconstructs readiness from configuration and current service evidence. Stored setup checkpoints are historical hints only and never override current unknown/failed checks. Invalid receipts remain untouched; read-only recovery can reconstruct remote state. Resolve the malformed local file before explicitly saving again. A concurrent configuration/progress change blocks replacement.

Save human confirmations with `setup-progress --event pat-ready --apply` or `--event secret-saved --apply`. This records an enum, not user text or a credential. Natural replies are sufficient. A resumed `pat-ready` needs confirmation that the user still has the PAT available before proceeding to GitHub; use `--event pat-unavailable --apply` when they explicitly say they need another. `secret-saved` followed by confirmed absence routes to repository/name/scope inspection rather than generating another PAT. Current Secret presence skips creation and storage. Native mode rejects runner credential events and checks its exact-config native receipt locally.

The checkpoint contains a format version, configuration digest, human-reported stage, observation time and boolean/unknown readiness checks. It contains no PAT, clipboard, browser snapshot, task text or merge authorization. Obtain existing setup PR context from the current checkout/branch and GitHub before creating a PR; retrieve its current head/base and review changes, reusing that PR when appropriate. Merge approval follows existing user authorization and the current reviewable PR, not a stored receipt.

## Explicit Plane App credential creation

For an authorized create-and-save request, follow
[the Plane App branch](local-credentials.md#automatic-creation-from-plane-app).
Recover using its operation UUID, expiry and config digest. Its non-secret receipt
is separate from setup's human-reported `pat-ready` event. Resume a pending local
Keychain copy instead of minting another PAT; an ambiguous creation first needs
Cloud metadata reconciliation. Missing login prompts Plane App login, while
storage/network/permission errors retain distinct statuses. Ordinary progress and
capability checks do not load desktop cookies or create credentials.

## Manual plugin version check

Run this only for an explicit request to check the plugin's own version. Resolve the helper from the actively installed plugin or standalone skill and run:

```sh
python3 /absolute/installed/skill-or-plugin/scripts/plane_workflow.py check-updates
```

The command works from any directory without a repository mapping, GitHub CLI or account login. `--offline` skips the request and reports the latest version as unknown. Normal `plane-start` preparation continues using `doctor` and read-only `setup-progress` for project synchronization; these paths do not invoke this command.

The check performs one anonymous GET to the canonical repository's latest stable GitHub Release endpoint. An isolated Python worker has a three-second total deadline, including DNS and response reads, with no retry loop or persistent cache. If that API is rate-limited/forbidden, one anonymous HEAD to the canonical latest-release link can identify its validated stable tag without following the redirect; both requests share the deadline. It reads no account credential store and sends no business mapping/task information. Only validated version metadata and the canonical release link enter the result; release prose and assets are discarded. See [GitHub's public release API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release).

`update_available` reports a newer stable plugin with its version and link. `current` matches the reported release; `ahead` means the installed version is newer, so no downgrade is offered. `unverified` leaves the latest version unknown on timeout, offline mode, unavailable/rate-limited upstream or invalid metadata. Report the result without an authentication/retry loop. Checking never installs, changes task/sync readiness or writes setup checkpoints; actual updates follow the user's selected installation channel and authorized scope.

A newer plugin notice does not establish which sync bundle it contains or whether the project needs it. Only an authorized plugin/skill update refreshes the installed catalog described below. This is a manual inspection command, separate from Skills CLI content-update tracking and background host/marketplace update settings.

## Sync bundle maintenance

Starting or resuming implementation uses `setup-progress --cache`; inspect `sync_bundle` and `maintenance_notice` there. Initial setup is not required for routine update detection. Pure discussion needs no account probes. `doctor` reports the plugin version, the packaged sync version and local bundle identity; only online progress establishes current Actions readiness.

Plugin and sync-bundle versions are independent. The installed plugin ships a trusted catalog of full SHA-256 fingerprints for the workflow and both runtime scripts, supported config schemas and PR binding protocol. Detection uses this installed catalog, not a network query for the latest upstream release; upgrading the plugin refreshes its knowledge. A project-provided version string alone is never proof. `remote_files_match` still means exact equality with the currently packaged bundle; `sync_bundle_verified` establishes recognized bytes and compatibility and is the readiness gate.

- `current`: continue when the other provider checks pass.
- `update_available`: the old bundle is supported. Continue the user's task and mention the optional update briefly; `next_step` remains connection verification rather than an upgrade.
- `upgrade_required`: known bytes fail the support/config/protocol policy. Report synchronization as not ready and propose a separate reviewed upgrade (`review_sync_bundle_upgrade`). Local task work can continue when independently authorized; distinguish pending background writeback.
- `unrecognized`: preserve customized/unknown bytes and inspect their differences (`review_sync_bundle_files`). Do not overwrite them or infer compatibility from the embedded version.
- `unverified`: reads failed or data is missing. Keep the result unknown and follow the reported probe issue; a failure does not justify replacing credentials.

Upgrade preparation, PR creation and merge follow the user's separate authorized scope and the existing `setup-github --upgrade` plan/hash/backup flow. Preserve project mapping, authorization, in-flight receipts, other worktrees and unrelated changes. Old setup checkpoints remain readable and are never reused as current compatibility proof. This is a skill-guided task check, not a background scheduler or an automatic upgrade hook.

## Handle the reported next step

| Result | Continue |
| --- | --- |
| `local_credential` | Read credentials.md; select the Plane account and check optional local credential reuse before requesting an existing PAT or creating a new one. |
| `confirm_pat_available_then_github` | Confirm availability, then guide storage without another creation. |
| `check_secret_repository_name_and_scope` | Inspect the mapped repository, exact name and runner scope. |
| `verify_secret_metadata` | Keep storage unknown; offer the exact GitHub link for an existing PAT, without requesting a new one. |
| `login_github` / `resolve_permissions` | Explain which probe failed, hand off login/SSO/permission resolution and preserve association. |
| `enable_actions` | Report disabled Actions and have an authorized repository administrator resolve it. |
| `retry_checks_later` | Respect service retry timing; rerun read-only checks when available. |
| `review_default_branch_setup` | Inspect/reuse the setup PR and trusted default-branch files, then complete activation with applicable authorization. |
| `run_connection_check` | Dispatch the trusted read-only check only after deployment; correlate the result to current default SHA and Secret update time. |
| `inspect_connection_failure` | Inspect the failed run safely. Distinguish expired PAT, project permissions, configuration and runner/policy/quota failures before requesting replacement. |
| `verify_native_mapping` | Observe actual official mapping/rules or obtain the user's specific confirmation; a paid plan alone is insufficient. |
| `connection_verified` / `native_verified` | Report provider evidence. Actual event writeback still needs separate evidence. |

Probe issues have a safe `code`, affected `stage`, `retryable` flag and next action. HTTP 401 means authentication; 403/SSO means permission; 404 can be hidden or absent; 429 means rate limiting. Network failures and malformed responses remain unknown. Neither errors nor an unverified UI page justify Secret replacement or switching API/provider modes. Keep GitHub runtime issues (disabled Actions, policy, billing/runner quotas) distinct from Plane credential errors. If the user cannot resolve a prerequisite now, report partial setup with the precise next step and lost background-sync capability.

UI navigation has a bounded recovery: one fresh inspection/retry when safe, then use the next route or manual steps. Stop observations before plaintext PAT generation/pasting; follow credentials.md for human handoff. For ambiguous creation/write failures, inspect existing projects/PRs/task state before retrying. Plane GET retries are bounded; uncertain writes on server/network failures are returned for reconciliation. No automated upgrade, acceptance, or duplicate provider writes.

## Daily synchronization observations

For routine implementation preparation use local-only `doctor --offline`, then `setup-progress --repo /absolute/repo --cache`. It writes only a non-secret cache under shared Git metadata and makes at most one routine GitHub metadata probe per repository mapping in 24 hours, including failed probes. Worktrees share this cooldown. It never dispatches Actions or reads a PAT. Explicit check-only requests omit `--cache` and `--apply`, leaving files unchanged; `--refresh` deliberately bypasses the metadata cooldown without dispatching a connection check. Offline checks keep current readiness unknown.

Reports separate configuration, connection observation time/source/freshness, and real event writeback. Connection or native UI evidence expires after 24 hours; expired evidence means refresh is due, not a broken integration. Continue independently authorized local development and keep PR-event synchronization enabled. Mention an unchanged stale observation once in the handoff rather than on every edit. A newer failed connection run supersedes older success. Native mode reads its local UI/user observation and never probes GitHub Secrets.

Refresh actual PAT access only during initial setup, an explicit revalidation request or authorized failure diagnosis using setup's read-only connection dispatch. Re-read its result with `check-github --refresh`. For native mode, obtain a new UI observation or current user confirmation. Cache/progress records do not prove human acceptance, current account access or a real PR write. No timer, background poll or automatic credential creation is installed.
