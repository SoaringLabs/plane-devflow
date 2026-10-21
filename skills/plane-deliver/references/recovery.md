# Capability detection and setup recovery

Read this at initialization, when resuming, or when a setup operation fails. Use `setup-capabilities` before requiring a repository or account; after a valid association use `setup-progress`. Both belong to `scripts/plane_workflow.py`.

## Detect and choose assistance

`setup-capabilities` detects local Git and GitHub CLI executables. Host UI capabilities cannot be inferred from installed apps: inspect the current tool inventory and pass repeated `--surface browser-control`, `--surface app-control` or `--surface url-opener` only for available tools. These flags report host capabilities, not authentication or permission grants. Tool refusal/disconnection changes the available route; remove the unusable surface and continue with the next available route. No surfaces defaults to manual clickable links. A Plane desktop installation is optional; use the configured Plane web origin when absent. Discover an authenticated session separately; a working MCP connection does not prove that a browser is logged in.

Before association, missing Git/repository/Plane authentication is a prerequisite to resolve, not permission to install apps, register accounts, upgrade plans or create replacement projects. Explain the current missing prerequisite and preserve successful authorization. This release's Git helper supports github.com only; GitHub Enterprise remotes need a supported adapter and must remain partial, without constructing github.com credential destinations for them. Self-hosted Plane uses the configured origins; verify account/API access and GitHub Runner network reachability rather than assuming the Cloud endpoints or bundled Cloud MCP can access that instance.

## Resume after association

Run `setup-progress --repo /absolute/repo --apply` to refresh remote evidence and persist a non-secret checkpoint. Add observed surfaces. It performs Git/GitHub reads and a local write under the Git common directory, never a service mutation. Check-only requests omit `--apply`. `--offline` is useful for local inspection but leaves Actions remote checks unknown. Missing gh permits manual credential storage, while automated verification remains pending; an available authorized GitHub connector may supply separately reported evidence, but does not turn the helper's unknown result into verified readiness.

Checkpoints are keyed by the entire validated configuration digest. Worktrees with the same mapping share progress; changed provider/project/rules/API routing uses another checkpoint and preserves the original. A new machine reconstructs readiness from configuration and current service evidence. Stored checks are historical hints only and never override current unknown/failed checks. Invalid receipts remain untouched; read-only recovery can reconstruct remote state. Resolve the malformed local file before explicitly saving again. A concurrent configuration/progress change blocks replacement.

Save human confirmations with `setup-progress --event pat-ready --apply` or `--event secret-saved --apply`. This records an enum, not user text or a credential. Natural replies are sufficient. A resumed `pat-ready` needs confirmation that the user still has the PAT available before proceeding to GitHub; use `--event pat-unavailable --apply` when they explicitly say they need another. `secret-saved` followed by confirmed absence routes to repository/name/scope inspection rather than generating another PAT. Current Secret presence skips creation and storage. Native mode rejects runner credential events and checks its exact-config native receipt locally.

The checkpoint contains a format version, configuration digest, human-reported stage, observation time and boolean/unknown readiness checks. It contains no PAT, clipboard, browser snapshot, task text or merge authorization. Obtain existing setup PR context from the current checkout/branch and GitHub before creating a PR; retrieve its current head/base and review changes, reusing that PR when appropriate. Merge approval follows existing user authorization and the current reviewable PR, not a stored receipt.

## Sync bundle maintenance

Starting or resuming implementation already refreshes read-only `setup-progress`; inspect `sync_bundle` and `maintenance_notice` there. Initial setup is not required for routine update detection. Pure discussion needs no account probes. `doctor` reports the plugin version, the packaged sync version and local bundle identity; only online progress establishes current Actions readiness.

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
| `plane_pat` | Read credentials.md; guide Plane creation first. |
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
