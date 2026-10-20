# 0.10.0 release validation

This is the first release named **Plane DevFlow**, from `SoaringLabs/plane-devflow`. Plugin/marketplace identities, the optional local npm installer, configuration paths, task directories and PR/comment markers now use the new name. The three skill identifiers remain unchanged. This is a naming migration boundary: previous-name runtime aliases and automatic business-data migration are not provided.

## Release checks

Checks cover Python regressions, npm installer and credential-isolation tests, actual local-tarball/full-plugin installation with native Codex discovery, standalone Skills CLI installation and helper startup, generated-source drift, package and Markdown resource validation, decision-eval corpus structure and the offline demo. Four-host installation checks distinguish file installation from optional native discovery and authenticated account use. Isolated profiles use empty credentials, a restricted environment and macOS filesystem/Keychain/Mach-service isolation verified before native clients start.

The 0.10.0 local candidate passed all 264 Python tests and all 23 npm installer/credential-isolation tests. Actual local tarball installation loaded the complete 28-file plugin and all three native Codex skills. Standalone Skills CLI checks, all 24 eval corpus structure cases, package validation, generated-source checks, resources across 63 Markdown files and the offline demo passed.

With Skills CLI 1.7.4 (also the registry latest at validation time), all four isolated host profiles passed project/global installation of all three skills, repetition, exact payload/helper checks and removal preserving synthetic settings/authentication and business mapping. Native discovery passed for Codex 0.163.0, Claude Code 2.1.301 and OpenCode 1.19.3. Cursor Agent 2026.10.19-6bbf2c4 required client login for skill loading; its MCP configuration check passed with `requires_authentication`. Configuration readback passed for the other three hosts. These results do not establish fresh OAuth completion.

Local source snapshots are checked before publication. Public GitHub installation and source/tag CI are separate checks; final results and run links are recorded in the [0.10.0 Release](https://github.com/SoaringLabs/plane-devflow/releases/tag/v0.10.0).

## Existing installations and migration

Read the [upgrade boundary](installation.md#upgrade-from-the-previous-name). This release does not rename business mappings, convert task receipts or PR bindings, or replace vendored synchronization files in other repositories. Existing credentials are not copied into test profiles or rotated. A local plugin refresh can retain an already migrated `plane-devflow` marketplace source and authorization, but does not establish compatibility with previous-name business records.

Previous tags and Releases retain the original product name. No `plane-devflow` npm package publication is required or performed for this GitHub/Skills CLI release.

## Unverified and limited items

- Fresh-client Plane OAuth and authenticated MCP access across all four agents. A registered URL or successful configuration readback is not authenticated tool access.
- Cursor native skill discovery and GUI acceptance without client login; historical connection failures are not treated as fixed by a rename.
- Model-driven end-to-end task workflows, multi-host decision quality, real PR writeback/state changes, and remote/cloud/SSH runtimes. No fresh model decision evaluation is claimed for the naming change.
- Native Claude Code, Cursor and OpenCode sessions on Windows/Linux. CI installation checks do not certify unavailable native host sessions.
- Automatic migration or continued loading of old-name configuration, receipts and PR markers; these are intentionally unsupported, not validated as compatible.
