# Publishing and contributing

Public source: [SoaringLabs/plane-for-codex](https://github.com/SoaringLabs/plane-for-codex). This is a community project distributed under the MIT License; GitHub publication does not imply inclusion in the official Codex catalog.

This repository is a generic plugin; no real user/project mapping or credential belongs in it. Example UUIDs are synthetic fixtures. Version is currently 0.4.2. Both legacy config version 1 and basic config version 2 are supported; PR binding protocol remains version 1. Old pinned Actions cannot read basic config version 2: resolve existing event workflows before changing the mapping. Full setup requires verified native or Actions synchronization; native requires observed mapping/rules and no runner Secret, Actions requires trusted remote files and runner verification; deferred credentials/workflow activation remain partial setup.

## Validate and publish source

1. Run `python3 -m unittest discover -s tests -v` and `python3 scripts/validate_package.py`.
2. Run the offline demo and inspect its outputs. Live MCP and Actions checks are separate from offline tests.
3. Review the exact publication file list and the reachable history of the branch being pushed. Remove private workspace/repository identities, real object IDs, private Actions run links and personal filesystem paths from public documents. Keep historical test totals, failures and limitations, and identify private evidence as unpublished. Exclude `.plane-for-codex.local/`, credentials, response snapshots, demo output and plugin caches; local Codex snapshot refs are not publication refs.
4. Commit the reviewed source and push only the intended branch (normally `main`) to this repository. Do not use `--mirror` or publish local snapshot refs. Repository creation, push and optional release tagging require an explicit publication request; installation testing does not publish automatically. The README includes clone and local-marketplace installation instructions.
5. Actions setup vendors two sync scripts and a workflow into each business repository; publishing this source is not needed for runtime. The official checkout dependency uses a verified full SHA. Existing users of the composite Action pin this repository's actual published commit SHA. Updating either copied scripts or a pin is a reviewed repository change; plugin installation cannot update other repositories' workflows automatically.

When changing a release, update `plugin.json` version and `plane_sync.VERSION` together, test compatibility, and reinstall the plugin to refresh its cached package. Keep the marketplace name stable. Onboarding should remain conversational and require only necessary account consent and project selection.

The repository's validation workflow runs tests, package validation and the offline demo on Python 3.10 and 3.14. After pushing, confirm repository visibility, the default branch, remote commit identity and both CI jobs. Source publication is separate from creating a version tag or GitHub Release.

## Verification scope

Version validation notes are historical records. The [v0.4.2 validation](docs/validation-0.4.2.md) includes the pre-publication rerun. The [live capability summary](docs/plane-github-capability-verification.md) is redacted; its raw private logs are not publicly accessible. An offline pass does not certify every host UI, self-hosted deployment, native integration or real PR writeback.

Report bugs with sanitized config shape, script version, operation and observed behavior. Do not include OAuth tokens, PATs, private task content or credential-bearing remotes. Contributions should preserve credential separation, idempotent delivery and manual-acceptance semantics.
