# v0.14.0 — One version for skills and GitHub synchronization

Plane DevFlow now uses one product version for its three skills, plugin, local helpers and public GitHub Action. One changelog describes the complete update; upgrading coordinates the local installation and the project's synchronization entrypoint.

## What changed

- New Actions setups use a small workflow pinned to the product's full release commit, instead of copying Python synchronization scripts into each project. The project keeps its mapping and Plane runner Secret.
- The unified upgrade flow verifies one release manifest and source snapshot, prepares a scoped project PR, refreshes the original local installation, and tracks installation, merge, activation and connection verification separately. Retrying PR creation reuses the existing PR.
- Upgrade checks preserve customized skill files, unrelated lock entries, the original installation scope and project mappings. Known legacy scripts are removed only after checking for other callers. Interrupted staging, backups and worktree creation can resume.
- Rollback prepares a separate reverse project diff and preserves later changes. Plugin updates retain an original-channel handoff and verify the active installation.

## Installation and upgrades

After the formal release and `stable` channel activation, install or refresh the complete standalone skill set from your target repository:

```sh
npx skills add https://github.com/SoaringLabs/plane-devflow/tree/stable --skill '*'
```

Add `--global` if that was the original installation scope, and open a new agent session afterward. Refreshing skill files alone does not update a project's Action pin.

For an existing project, ask: **“Use plane-setup to upgrade Plane DevFlow in this repository. Show the target version, changelog and change plan first.”** Review the project PR, activate the change and verify synchronization through that flow. Publication does not migrate existing repositories automatically. See [installation](https://github.com/SoaringLabs/plane-devflow/blob/v0.14.0/docs/installation.md) and [product upgrades](https://github.com/SoaringLabs/plane-devflow/blob/v0.14.0/plugins/plane-devflow/references/product-upgrades.md).

## Compatibility and validation

The public skills remain `plane-setup`, `plane-start` and `plane-deliver`. Mapping schemas 1/2 and PR binding protocol 1 remain supported. New basic mappings record PR activity without changing task states; legacy mappings retain their rules and native integrations retain event ownership. Manual acceptance remains separate from merging.

Implementation and review checks passed 500 Python tests and 23 Node tests. The merged implementation passed all 10 remote CI jobs, including Linux/macOS/Windows installation checks. Isolated real GitHub/Plane validation confirmed public Action execution, lifecycle comment updates, retry idempotency, stale-event readback and trusted configuration. The test task's state remained unchanged.

Formal release-asset resolution and public `stable` installation are publication-time checks and are not established by candidate tests. Native plugin refresh, other hosts' native clients, model sessions and business-project migration are outside that live test scope. No npm publication is required for Skills CLI installation.

See the [changelog](https://github.com/SoaringLabs/plane-devflow/blob/v0.14.0/CHANGELOG.md), [review](https://github.com/SoaringLabs/plane-devflow/blob/v0.14.0/docs/review-0.14.0.md) and [release preparation record](https://github.com/SoaringLabs/plane-devflow/blob/v0.14.0/docs/release-readiness-0.14.0.md) for detailed evidence and remaining gates.
