# Install, update, migrate and remove

[English README](../README.md) · [中文说明](../README.zh-CN.md)

## Install with npx

```sh
npx plane-for-codex@latest
```

Requirements: Node.js 20+, npm and a plugin-enabled Codex CLI on PATH (verified with 0.163.0). Runtime Python helpers need Python 3.10+; PR operations need Git and an authenticated GitHub CLI. The installer does not install or replace those tools.

The npm package includes the complete plugin: three skills, shared Python helpers and references, branding and Plane MCP configuration. On a fresh install it saves an immutable version under `~/.codex/marketplaces/plane-for-codex-npm/versions/<version>/plugin` (or the configured Codex state directory), then registers that persistent marketplace and installs through Codex. Registration never points into the disposable npm/npx cache. An official Codex directory listing is not required.

Before reporting success, the installer checks the native installed/enabled result, compares the complete source and installed payload by SHA-256, and asks Codex's native loader to confirm all three enabled skills. A registration success alone is insufficient. Native loading does not verify live Plane access or business writeback.

Open a new Codex chat in the target business repository and select **Set Up Plane**. Setup reuses existing authentication and asks for browser authorization only when missing or expired. Installation, account authorization, project association and background synchronization remain separate results.

## Update or inspect

Rerun the installation command to update. For a read-only installation check:

```sh
npx plane-for-codex@latest --check
```

Add `--json` for machine-readable results, or `--help` for usage. npm-managed sources use the plugin version bundled with the selected installer. Previous version directories remain available; modified managed payloads are preserved and cause an explicit error rather than being silently replaced. Repeated installs reuse the marketplace registration.

## Existing local marketplace installations

The installer keeps any existing `plane-for-codex` registration and its account authorization. It does not repoint a local checkout or a custom Git source to its own bundle.

- Existing Git marketplaces refresh the same configured source/ref through Codex, then reinstall. Pinned refs retain their own pin.
- Existing local development checkouts retain local modifications. Update that checkout through your usual Git workflow, then run the npx installer; it reports the actual selected source and installed version, which can differ from the npm installer's bundled version.
- `--check` inspects the selected installation without refreshing a source or reinstalling.

To deliberately switch an old local or Git source to npm-managed distribution, first preserve local changes and note the old path. Remove only the marketplace registration, then run the npx installer:

```sh
codex plugin marketplace remove plane-for-codex
```

This is a source migration, not permission to delete the old checkout or reset shared Plane authorization. Business repository mappings, task workspaces and copied synchronization files stay separate.

## Native Git marketplace alternative

Users who prefer Git-backed distribution can still install the complete plugin directly:

```sh
codex plugin marketplace add SoaringLabs/plane-for-codex && \
  codex plugin add plane-for-codex@plane-for-codex
```

Here `marketplace` means the catalog in the GitHub repository, not the official public Codex directory. The first command registers that source; the second installs `plugin-name@marketplace-name`. Do not replace an existing registration just to follow this alternative.

Contributors can register their chosen repository path with `codex plugin marketplace add "$PWD"`, then install `plane-for-codex@plane-for-codex`. Keep the selected local source and review its changes. See [CONTRIBUTING](../CONTRIBUTING.md).

## Remove the plugin

```sh
codex plugin remove plane-for-codex@plane-for-codex
```

This removes the installed plugin/cache. The npm-managed source and registration remain so reinstalling is possible. It does not remove business-repository `.plane-for-codex.json`, copied workflows/scripts, task worktrees or external integration settings. Background synchronization may continue until an authorized change disables it in that repository or official integration.

## Distribution and verification

The npm package is the installer and the full versioned plugin bundle. `npx` fetches/runs it; Codex remains responsible for native registration and installation. Standalone copies of individual skill folders are insufficient for this package because they omit shared resources and MCP configuration.

See [npm exec/npx](https://docs.npmjs.com/cli/v11/commands/npm-exec/), [OpenAI marketplace packaging](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli) and the [npm installation validation record](validation-npx.md). Historical native Git and README checks remain in [the earlier validation record](validation-readme.md).
