# Publishing and contributing

This repository is a generic community plugin; no real user/project mapping or credential belongs in it. Example UUIDs are fixtures. Version is currently 0.1.0.

1. Run `python3 -m unittest discover -s tests -v` and `python3 scripts/validate_package.py`.
2. Run the offline demo and inspect its outputs. Live MCP and Actions checks are separate from offline tests.
3. Create the user's chosen public GitHub repository, push this source and optionally tag a release. Publishing is a separate explicit user action; installation testing does not publish automatically.
4. Share the repository and local-marketplace install instructions in README. Codex official catalog inclusion is separate and is not promised.
5. Users enabling Action sync must pin this repository's actual published commit SHA. Updating that pin is deliberate; plugin installation cannot update other repositories' workflows automatically.

When changing a release, update `plugin.json` version and `plane_sync.VERSION` together, test compatibility, and reinstall the plugin to refresh its cached package. Keep the marketplace name stable. Onboarding should remain conversational and require only necessary account consent and project selection.

Report bugs with sanitized config shape, script version, operation and observed behavior. Do not include OAuth tokens, PATs, private task content or credential-bearing remotes. Contributions should preserve credential separation, idempotent delivery and manual-acceptance semantics.
