# Publishing and contributing

Public source: [SoaringLabs/plane-devflow](https://github.com/SoaringLabs/plane-devflow). Plane DevFlow is a community project distributed under the MIT License; GitHub publication does not imply inclusion in the official Codex catalog.

This repository is a generic plugin; no real user/project mapping or credential belongs in it. Example UUIDs are synthetic fixtures. Version is currently 0.10.0. Both legacy config version 1 and basic config version 2 are supported; PR binding protocol remains version 1. Old pinned Actions cannot read basic config version 2: resolve existing event workflows before changing the mapping. Full setup requires verified native or Actions synchronization; native requires observed mapping/rules and no runner Secret, Actions requires trusted remote files and runner verification; deferred credentials/workflow activation remain partial setup.

## Version policy

Choose the version for the scope of a reviewed release, rather than for each edit. Documentation, installation guidance, validation adjustments and compatible bug fixes normally increment the patch version (`0.9.0` → `0.9.1`). Group meaningful new capabilities into a minor release; clearly flag incompatible changes and provide migration notes. Small edits can accumulate before a release. Preserve existing configuration and authorization unless a deliberate migration is authorized.

The 0.10.0 rename changes runtime/configuration identities without old-name aliases. This is a migration boundary in the pre-1.0 series, rather than a documentation-only patch. Preserve previous release tags and disclose the upgrade limits.

## Validate and publish source

1. Run `npm ci` and `npm test`; inspect `npm pack --dry-run --json` against the complete plugin file list. Install `requirements-dev.txt` in a development virtual environment, then run `python3 -m unittest discover -s tests -v` and `python3 scripts/validate_package.py`.
2. Validate the behavior cases with `python3 evals/run.py --validate-only`; run affected fresh-session decision evals as described in [evals/README.md](evals/README.md), recording model/configuration, source digest and limits separately from live integration evidence. Run the offline demo and inspect its outputs. Live MCP and Actions checks are separate from offline tests.
3. Review the exact publication file list and the reachable history of the branch being pushed. Remove private workspace/repository identities, real object IDs, private Actions run links and personal filesystem paths from public documents. Keep historical test totals, failures and limitations, and identify private evidence as unpublished. Exclude `.plane-devflow.local/`, credentials, response snapshots, demo output and plugin caches; local Codex snapshot refs are not publication refs.
4. Commit the reviewed source and push only the intended branch (normally `main`) to this repository. Do not use `--mirror` or publish local snapshot refs. Repository creation, push and optional release tagging require an explicit publication request; installation testing does not publish automatically. The README uses Skills CLI to install self-contained folders directly from GitHub. The npm installer can be tested locally before a separately authorized npm publication. Contributor clone and local plugin installation instructions live in docs/installation.md.
5. Actions setup vendors two sync scripts and a workflow into each business repository; publishing this source is not needed for runtime. The official checkout dependency uses a verified full SHA. Existing users of the composite Action pin this repository's actual published commit SHA. Updating either copied scripts or a pin is a reviewed repository change; plugin installation cannot update other repositories' workflows automatically.

When changing a release, update `plugin.json` version and `plane_sync.VERSION` together, test compatibility, and reinstall the plugin to refresh its cached package. Keep the marketplace name stable. Onboarding should remain conversational and require only necessary account consent and project selection.

Record version changes in [CHANGELOG.md](CHANGELOG.md). Keep the README focused on current capabilities, installation and usage, with a link to the changelog instead of inline version history.

The repository's validation workflow runs Python tests, package validation and the offline demo on Python 3.10 and 3.14; Node.js 20/24 installer checks include actual npx/native loading on macOS, Linux and Windows. After pushing, confirm repository visibility, the default branch, remote commit identity and every Python/installer CI job. Source publication is separate from creating a version tag or GitHub Release.

## Publish the standalone skills

Run `python3 scripts/build_skills.py`, review and commit the generated `skills/` directory with its canonical sources, then run the generation drift check, package validation and `npm run test:skills`. Exercise actual Skills CLI discovery and installation from an isolated source snapshot before publication. No Plane-owned npm publication is needed for Skills CLI distribution. The public repository command cannot validate an unpublished local candidate; test the candidate snapshot and report this limit explicitly.

MCP dependency metadata, registered configuration, an unauthenticated transport probe and authenticated workspace access are distinct evidence. Tests use empty credential stores. Never copy existing OAuth tokens into a test profile. Verify project/global scope, individual skill installation and preservation of existing connections and business configuration. Validate the complete plugin as well as the standalone skills; its qualified identifiers and npm installer use the same canonical source.

## Publish the npm installer

The npm installer is an optional complete-plugin distribution. The `plane-devflow` npm package has not been published. Skills CLI installs directly from GitHub and does not require an npm publication. When publishing a new npm tarball, the public package is `plane-devflow`; its version must match `plugin.json` and `plane_sync.VERSION`. Its executable is `bin/plane-devflow.mjs`. The npm `files` allowlist includes the full plugin and excludes tests, evals, private evidence, development dependencies and Python bytecode.

After all source checks, pack into an isolated output directory. Extract that exact tarball, compare every plugin file to the reviewed source, install via actual npx with a fresh Codex state, and verify repeat/check/retained-source behavior. Test native loading separately from mocked command tests. Preserve the user's real configuration/authentication; never copy credentials into the test profile.

For an authorized publication, confirm npm identity with `npm whoami`, publish the reviewed tarball with public access, then read back its version, integrity and `latest` tag from the public registry. Finally run the exact public README command against a fresh cache/state and confirm native skill discovery. Browser login and any registry 2FA remain user actions; credentials never pass through chat. Keep npm publication, GitHub source/CI and any optional GitHub Release as separate read-back facts.

## GitHub Marketplace

The root `action.yml` describes the composite Action, so GitHub may show a banner inviting publication to GitHub Marketplace. This is an optional Action listing, separate from distributing the Codex plugin. Current Actions setup copies a workflow and synchronization scripts into the business repository; it does not require this Marketplace listing.

Consider a listing if the composite Action is promoted as a standalone reusable component with its own usage documentation and versioned releases. GitHub documents publication through a tagged release and the "Publish this Action to the GitHub Marketplace" option; the banner alone does not publish anything. See [Publishing actions in GitHub Marketplace](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace).

## Verification scope

The [v0.10.0 validation](docs/validation-0.10.0.md) covers the first Plane DevFlow release, credential-isolated installation checks and explicit naming migration limits. Final source/tag CI and publication readbacks are recorded in its Release.

The [v0.9.1 validation](docs/validation-0.9.1.md) records the project-scope installation guidance patch; final public-source, CI and local-update readbacks are linked from its Release.

The [v0.8.0 release-candidate validation](docs/validation-0.8.0.md) joins the skill, README and native-install evidence, keeping their original source versions and limits explicit.

The [README validation](docs/validation-readme.md) records bilingual presentation, native installation command checks, HTML resources and local visual previews.

The [skill-quality validation](docs/validation-skill-quality.md) records package checks, synthetic decision evaluations and their limits separately from live integration evidence.

The [v0.7.0 validation](docs/validation-0.7.0.md) covers isolated parallel tasks, task PR routing and base-conflict resolution. The [v0.6.1 validation](docs/validation-0.6.1.md) covers first-write task ownership, discussion/document intent and local installation. The [v0.6.0 validation](docs/validation-0.6.0.md) covers checkout guards, completion handoff and local installation. The [v0.5.0 validation](docs/validation-0.5.0.md) covers task receipts and evidence gates. Version validation notes are historical records. The [v0.4.2 validation](docs/validation-0.4.2.md) includes the pre-publication rerun. The [live capability summary](docs/plane-github-capability-verification.md) is redacted; its raw private logs are not publicly accessible. An offline pass does not certify every host UI, self-hosted deployment, native integration or real PR writeback.

Report bugs with sanitized config shape, script version, operation and observed behavior. Do not include OAuth tokens, PATs, private task content or credential-bearing remotes. Contributions should preserve credential separation, idempotent delivery and manual-acceptance semantics.
