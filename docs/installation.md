# Install, update, migrate and remove

[English README](../README.md) · [中文说明](../README.zh-CN.md)

## Native installation

For a new installation, paste:

```sh
codex plugin marketplace add SoaringLabs/plane-for-codex && \
  codex plugin add plane-for-codex@plane-for-codex
```

This is one paste containing two native CLI operations: register the Git-backed marketplace, then install the plugin only if registration succeeds. Codex manages the repository checkout and plugin cache. It does not install Git, Python, Codex or GitHub CLI for you.

Requirements: a plugin-enabled Codex CLI, Git, Python 3.10+, and an authenticated GitHub CLI for PR operations. The complete native installation and three-skill discovery were verified in fresh isolated environments with CLI 0.163.0; see the [validation record](validation-readme.md). Marketplace installation availability varies by client/workspace policy. The repository marketplace is a community distribution source, not an official-directory listing.

The source URL is `https://github.com/SoaringLabs/plane-for-codex.git`; its `.agents/plugins/marketplace.json` points at `plugins/plane-for-codex`. The complete plugin includes three skills, shared Python helpers/references, assets and Plane MCP configuration. Standalone `npx skills add` copies are not a supported substitute for this bundle.

Open a new chat in the target business repository, then select **Plane: 初始化**. Setup reuses existing authentication and asks for browser authorization only when missing or expired. Plugin installation, Plane authorization, project association and background-sync verification are separate results. OAuth approval remains a user action; never paste credentials into chat.

If the marketplace/installation step fails, inspect that error before continuing. Do not claim a complete installation from successful registration alone. Use `codex plugin marketplace list` and `codex plugin list --marketplace plane-for-codex` to inspect the configured source and installed plugin. Seeing the three skills in a new chat verifies discovery only, not real service access.

## Update a Git-backed installation

```sh
codex plugin marketplace upgrade plane-for-codex && codex plugin add plane-for-codex@plane-for-codex
```

Open a new chat afterward. Marketplace upgrade refreshes source; reinstall refreshes the cached plugin. It does not upgrade copied workflow/synchronization scripts in business repositories. Those updates follow a separate reviewed plan in the affected repository.

## Existing local marketplace installations

Earlier instructions registered a manually cloned local directory under the same marketplace name. Keep that source if you are developing the plugin or have local modifications. Update your chosen local checkout through your normal Git workflow, then reinstall:

```sh
codex plugin add plane-for-codex@plane-for-codex
```

Do not replace a local source just to follow the new quick start. Inspect `codex plugin marketplace list` first. If you explicitly want Git-managed distribution, preserve local changes, note the old source path, remove only its marketplace registration, then use the native installation command:

```sh
codex plugin marketplace remove plane-for-codex
```

Marketplace removal changes the registration; it is not permission to delete your clone, business repository or task workspaces. Do not remove shared Plane MCP connections. If client policy prevents source replacement, retain the working installation and resolve that policy separately.

## Development from a local checkout

Contributors can keep the local path workflow:

```sh
git clone https://github.com/SoaringLabs/plane-for-codex.git
cd plane-for-codex
codex plugin marketplace add "$PWD"
codex plugin add plane-for-codex@plane-for-codex
```

This installs the selected local source. It neither publishes changes nor replaces account authorization. Preserve existing registered sources instead of silently repointing the same marketplace name. Development dependencies and validation are in [CONTRIBUTING](../CONTRIBUTING.md).

## Remove the plugin

```sh
codex plugin remove plane-for-codex@plane-for-codex
```

This removes the installed plugin and its cache. It does not remove business-repository `.plane-for-codex.json`, copied workflows/scripts, task worktrees or external integration settings. Background sync may therefore continue until an authorized change disables it in that repository or official integration. Review those resources separately before changing them.

## Reference

The native Git marketplace interface is documented in [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli). No npm package or remote bootstrap script is needed for this installation path. See the repository's [validation record](validation-readme.md) for the scope of checks performed on these instructions.
