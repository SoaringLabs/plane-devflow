# README presentation and installation — pre-release evidence

This record describes the pre-release implementation/testing phase. Publication and the version bump are tracked separately in [v0.8.0 release validation](validation-0.8.0.md); statements below about no publication apply to that phase.

Date: 2026-10-20. Work continues on `codex/skill-quality`, based on `3e1245b28e5563e7de03421f1bfd25328267f528`. No push, PR, tag, npm package or Release was created. Existing runtime helpers, skill behavior, authorization boundaries and user installation were preserved.

## Requested changes

- `README.md` is the complete English default, with `README.zh-CN.md` providing the corresponding Chinese version and a top-level switch in both directions.
- Both entrypoints use the existing logo, product name, live GitHub release/Stars/main-CI badges, MIT/Python badges, short positioning, navigation and an original SVG workflow illustration. The illustration is labeled as a schematic, with an example task; it does not claim to be a product screenshot.
- Quick start uses one copyable shell command containing native marketplace registration and plugin installation, joined by `&&` so installation stops on registration failure. Shell line continuation keeps the command readable. It removes manual clone/cd/absolute-path steps for new users without introducing a Node/npm bootstrap dependency.
- Browser account authorization and background-sync configuration remain separate. Existing local sources have an explicit preservation/migration path. Update/remove instructions distinguish plugin files, business-repository copies, task workspaces and account configuration.
- Further content follows the reference's hierarchy: quick start, benefits, skills, synchronization, scope, updates and deeper documentation. All copy describes current capabilities.

Reference inspected: [HyperFrames README](https://github.com/heygen-com/hyperframes/blob/main/README.md). Native marketplace source handling was checked against [OpenAI packaging documentation](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli), local CLI 0.163.0 help, and the CLI's plugin/marketplace source code. No assets or branding were copied from the reference project.

## Installation verification

- `codex plugin marketplace add`, `plugin add`, `marketplace upgrade` and `plugin remove` syntax checked against the local CLI help.
- Live `origin/main` and remote HEAD both resolved to the base commit above. A fresh shallow clone of that public source passed current payload validation: three skills and eleven linked plugin Markdown files. The remote marketplace name/path matches the command's selector and complete plugin.
- The exact README command was executed successfully in a fresh temporary Codex state directory using CLI 0.163.0, without the shared daemon. It registered the public Git marketplace and installed/enabled the complete v0.7.0 plugin. Native `skills/list` changed from zero Plane skills before installation to all three enabled `plane-for-codex:*` skills afterward, with the correct plugin ID/cache paths and no load errors.
- All 26 public payload files matched the downloaded source by SHA-256, including the manifest, Plane MCP configuration, logo, shared helpers/references and three skills with agent metadata. The source commit was `3e1245b28e5563e7de03421f1bfd25328267f528`. The unreleased candidate was separately staged without development bytecode caches and installed through a local marketplace in another fresh state directory: all 28 payload files matched and all three skills loaded/enabled without errors. This second check verifies the local candidate; the public README command still installs the public source until publication is authorized.
- Isolation used child-process state configuration, file-based credential stores and a macOS sandbox denying writes under the real user directory and reads of existing Codex configuration, credentials, plugin/skill directories and keychain files. The original shell environment was unchanged. A write probe to the real Codex directory was denied with `Operation not permitted`; 59 protected configuration/authentication/Plane-plugin path entries had identical before/after hashes. No credentials were copied, no login or business-repository writes were performed, and both native server processes exited.
- Installed `plane_workflow.py --help` and `plane_sync.py --help` passed with Python 3.14.3 in both environments. Earlier verifier assertions were corrected to recognize the native plugin-qualified skill names, exclude development bytecode from candidate staging, and exercise actual CLI entrypoints rather than library modules; these were harness corrections, not plugin fixes. Raw attempt outputs are retained outside the publishable source tree. Aggregate results are in [native installation results](validation-native-install.json). Package validation, all 18 package regression tests and `git diff --check` passed again after the record update. OAuth and real service writeback remain untested.
- The shorter native command already points at the existing public marketplace, rather than an unpublished npm package or a not-yet-published install script. New README/SVG files themselves remain local until publication is authorized.

## Static and visual checks

The package checker now follows both inline Markdown and HTML `a`/`img` resources, including language switches, logo/hero paths and heading anchors. It checks both README installation sources/selectors after parsing the shell command and its continuation. Regression fixtures reject a broken HTML image, missing navigation anchor, divergent Chinese selector or installation chain that continues after failure.

Local GitHub-style previews cover English and Chinese at desktop width 1280, mobile width 390, and desktop dark mode. Image loading, whole-page overflow and both language-switch directions are inspected. These are local Markdown renders, not GitHub-native/client acceptance screenshots. On mobile, tables and command blocks scroll inside the page as on GitHub.

| Check | Observed result |
| --- | --- |
| Full Python suite | 255 tests passed in 166.207 seconds |
| Package regression subset | 18 tests passed, including the new HTML/translation/command-chain fixtures |
| Package validator | Three skills, thirteen plugin Markdown files and thirty-two repository Markdown files checked; passed |
| Eval corpus structure | 24 cases valid; skill decision behavior was unchanged in this README-only follow-up |
| Local visual previews | English/Chinese × desktop/mobile/dark: six checks passed, no broken images or page-level overflow |
| Language switch | Both directions passed in the local preview |
| Source payload | Fresh public clone passed three-skill/eleven-Markdown payload validation |
| Actual native install | Exact public command passed; complete public and unreleased candidate bundles matched 26/28 source files by SHA-256 |
| Actual native discovery | Both environments loaded/enabled all three plugin-qualified skills; zero load errors |
| Existing configuration | Sandbox write probe denied; 59 protected path entries unchanged by hash |
| Diff hygiene | `git diff --check` passed |

During editing, an earlier full run correctly rejected a link to this validation record before the file existed. The record was then added, the targeted tests passed, and the final complete run above passed without waivers. The earlier failed output remains in local task evidence.

The local preview used a GitHub-style renderer and isolated headless Chrome, rather than the GitHub production renderer. Native CLI installation and app-server skill discovery passed in isolation; account authorization, event writeback, desktop UI acceptance and remote CI remain unverified in this follow-up. The localhost preview is retained for user review; no public website was deployed.
