# Unified product upgrades

Use this only for an explicit Plane DevFlow installation/project upgrade, migration or rollback request. Ordinary task preparation remains read-only and never updates skills or workflows. Keep the three public skills and use the original installation channel.

## Select one release and one scope

Resolve the installed helper's absolute path. Inspect the current repository mapping, selected agent, project/global installation and any saved upgrade record. For plugin installations, resolve the actual active plugin source before planning; do not install standalone skills alongside it.

An explicit version check can use `check-updates`; it reports a release without installing it. For a chosen formal target, run:

```sh
python3 /absolute/installed/scripts/plane_workflow.py resolve-release --target-version VERSION
```

Save its returned JSON outside tracked files as the release manifest. It must identify a published stable release, the tag's actual full commit and the product manifest asset. A missing manifest on a historical release is a migration limitation, not permission to substitute `main` or invent a commit. Unpublished candidates use isolated fixtures and separate development validation.

Release metadata requests reuse the existing GitHub CLI login. If the CLI is unavailable or unconfigured, public anonymous reads remain available; invalid credentials and permission errors require their own recovery. No additional PAT or credential transfer is needed. Downloads of the public manifest remain unauthenticated and restricted to GitHub asset hosts.

Routine pinned-version checks may reuse a validated public release identity for up to one hour across local repositories. The cache stores only the version, full commit, asset ID, manifest digest and public manifest under `$XDG_CACHE_HOME/plane-devflow/releases` (default `~/.cache/plane-devflow/releases`); it never stores credentials or project readiness. `evidence.product_release` identifies the source and observation time. `latest`, explicit `resolve-release`, and final `upgrade --step verify --apply` read the remote identity again. Failed refreshes cannot fall back to cached success. An unavailable cache does not block live reads.

On `rate_limited`, report the affected step and UTC `retry_at`, then wait until that time before an explicit retry. Shared cooldown records suppress repeated requests through the same transport; they do not create scheduled retries. Authentication failures must not trigger an anonymous retry. Never substitute a web page, local candidate or saved connection result for the missing formal identity check.

Show the changelog, exact target version/commit, original installation channel/scope and affected repository. A global skill refresh also affects other projects using that installation; it does not update their workflows. Multi-project requests require an explicit list; handle each project independently.

## Prepare before applying

The following helper names are implemented; replace placeholders with verified values:

```sh
python3 /absolute/installed/scripts/plane_workflow.py upgrade --repo /absolute/project \
  --step plan --release-file /tmp/product-release.json --host codex --scope project
```

For the original plugin channel, add `--channel plugin --plugin-root /absolute/active/plugin`. Review the returned project diff, installation snapshot and plan ID. Repeat the identical plan with `--apply --expected-plan-id PLAN_ID` to save its immutable non-secret record in shared Git metadata. This records progress, not human authorization.

Within the approved upgrade scope, run the saved plan's independent stages:

```sh
python3 /absolute/installed/scripts/plane_workflow.py upgrade --repo /absolute/project --plan-id PLAN_ID --step stage --apply
python3 /absolute/installed/scripts/plane_workflow.py upgrade --repo /absolute/project --plan-id PLAN_ID --step project --apply
```

Staging verifies the complete fixed source before execution. Project preparation fetches the recorded base and makes an isolated upgrade worktree; mapping, default-branch or file drift requires a fresh reviewed plan. Preserve customized workflow/scripts. Extra listeners or callers of the legacy scripts require separate review before replacement or deletion. Native provider projects retain official synchronization ownership.

Inspect the resulting diff. The `pr` stage commits only planned files and pushes/creates or reconciles one upgrade PR; run it with `--apply` only within explicit PR authorization. It never merges. An uncertain create response requires reading existing PRs before retrying; the stable plan marker identifies the same upgrade.

The `install` stage with `--apply` refreshes all three Skills CLI payloads from the same fixed product source and verifies installed bytes and the selected host entry. Customized host copies, redirects, changed installation environments and unrelated skill metadata stop installation before overwriting them. Project PRs preserve other skills' lock entries. When project skills or their metadata are tracked in Git, stage their changes in the isolated upgrade workspace before the `pr` stage; the original checkout stays unchanged. After merge, rerun `install` to fast-forward a clean original base checkout and verify its installed bytes. A busy or different branch receives an explicit synchronization handoff. Credentials remain separate. The pinned Skills CLI requires Node.js 22.20+.

For a plugin installation, `install` returns a manual handoff through its original channel. Reopen the host when required, resolve its actual active plugin directory, then use `--step confirm-plugin --plugin-root /absolute/active/plugin --apply`. Hosts may activate a new versioned cache path; the helper verifies its complete target payload and records that path without replacing the original plan. Later status checks re-read those active files. Never register MCP again just to update files.

## Resume, activation and verification

Read progress with `upgrade --step status --repo ... --plan-id ...`. The record lives outside the installed skills, so a new session can resume it. After staging, the CLI verifies and delegates later stages to the staged helper in a fresh process. Replacing the active installation does not replace the running coordinator. Interrupted source/backup copies and worktree preparation can be retried; modified files are preserved for review. Inspect a stale process lock before removing it; do not remove a live updater's lock.

Local installation, project PR, activation and verification are independent progress fields. Reuse prior authorized scope after interruption; a record cannot grant missing merge or write permission. Check current Git/PR/installed facts before advancing. A candidate source, local tracking ref or cached run is not live production evidence.

Before merge, inspect running/queued old sync jobs and retain a single listener path and the existing concurrency/PR comment identity. Merge requires its existing separate authorization. After activation, use `upgrade --step verify --apply` for explicit metadata refresh and a connection-result read. This stage does not dispatch a workflow or write Plane. If a new connection run is needed, prepare its exact target and use the existing setup flow within that scope.

Report the selected version, local installation, PR link, activated reference and connection result separately. Tracked project skills must match the target on the actual activation branch, including native-provider projects. Only the required selected steps count toward upgrade completion. Real PR-event writeback is reported independently; never create a task or test PR merely to fill that evidence gap without scope.

The verify result's `verification_steps` separates local installation, activation, release identity, observed connection and overall verification. A successful connection may coexist with `verification_pending` when identity checks are unavailable; preserve that distinction and the structured issue. The existing top-level completion fields still require all gates.

## Rollback

`upgrade --step rollback` previews the saved reverse project changes; `--apply` prepares an isolated reverse diff from the current base. Review that diff and deliver a separate rollback PR within the user's scope. It does not reset the default branch, merge, replay events or downgrade local skills.

Inspect the paired local installation downgrade through its original channel after the repository plan is concrete. An old local release may not recognize the new Action layout. Preserve later mapping/workflow edits and receipts; do not treat local downgrade alone as a completed rollback.
