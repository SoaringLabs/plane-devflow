# v0.8.0 release-candidate validation

Date: 2026-10-20. Scope: the bilingual README, native marketplace installation guide, three skill entrypoints, conditional delivery/finalization references, development package validation and synthetic decision evals. This version also includes the previously published main-branch acceptance-environment guide and branding updates since v0.7.0.

## Version and compatibility

`plugin.json` and `plane_sync.VERSION` both identify 0.8.0. Marketplace/plugin identities, the Plane MCP endpoint, three skill names, runtime dependencies, mapping schemas and authorization boundaries are retained. Runtime implementation changes in this release preparation are limited to the version constant; the skill procedures and documentation preserve their existing operational gates. Existing plugin installation does not upgrade copies of Actions scripts or workflow pins in business repositories.

## Evidence from the implementation phase

- [Skill authoring and decision evaluation](validation-skill-quality.md): 24 synthetic cases for both original/candidate entrypoints, plus 12 finalization follow-up sessions. Original scores and rubric corrections are retained. This is decision evidence rather than real service execution.
- [README and installation](validation-readme.md): six local visual previews, both language switches, a fresh public v0.7.0 installation and a separate local candidate installation, full payload hashes, all three enabled native skills and existing configuration preservation. [Machine-readable installation evidence](validation-native-install.json) retains that phase's original version and source commit.
- README visual acceptance and isolated installation were confirmed before release preparation. The original primary checkout's pre-existing untracked instructions are excluded from publication.

## Final candidate checks

All checks below ran after the version bump, before source publication:

| Check | Observed result |
| --- | --- |
| Full Python 3.14.3 suite | 255 tests passed in 249.025 seconds |
| Package validation | Passed: 3 skills, 13 linked plugin Markdown files and 33 repository Markdown files |
| Eval corpus structure | All 24 cases valid; no skill wording changed during version preparation |
| Offline demo | Passed; `live_services_called=false` |
| Fresh native candidate install | CLI 0.163.0 installed/enabled the local 0.8.0 bundle in an isolated state directory |
| Installed payload | All 28 source files matched the installed files by SHA-256 |
| Native skills | All three plugin-qualified skills enabled, paths inside the 0.8.0 cache; zero load errors |
| Existing installation/configuration | Sandbox write probe denied; protected configuration/authentication/Plane-plugin path hashes unchanged during the isolated check |
| Publication review | New source reviewed for personal paths, credential-like tokens and private project identities; raw evidence excluded |
| Diff hygiene | `git diff --check` passed |

The versioned native check used a separately staged local marketplace because the release had not yet been published. The public Git installation command was previously exercised against its actual published source, as recorded in the historical installation evidence. Remote CI and the final installed user profile are verified separately after publication, rather than inferred from the local candidate.

## Boundaries

OAuth, live Plane/MCP operations, real business PR writeback and desktop UI skill selection are outside this release-candidate verification. GitHub source publication, CI, the tag/Release and the installed local plugin are read back separately during the authorized release process. Private raw transcripts, configuration/authentication snapshots and local preview files remain outside the tracked source tree.
