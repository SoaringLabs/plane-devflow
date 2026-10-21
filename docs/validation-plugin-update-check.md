# Manual plugin update check candidate validation

This unpublished candidate is based on plugin 0.10.2 and sync bundle 0.10.1. It adds an optional manual command while retaining ordinary task preparation. No release, tag, npm publication, local plugin update or business workflow upgrade is performed.

## Behavior and boundaries

`plane-start` continues to run `doctor` and read-only `setup-progress` for project synchronization. Its instructions and the onboarding progress implementation are unchanged from released 0.10.2; neither calls the plugin-version checker. Sync-bundle compatibility still uses the installed plugin's reviewed fingerprints/configuration/protocol catalog, with supported older bundles remaining ready. Actual sync runtime/workflow bytes remain unchanged.

For an explicit version-check request, `plane_workflow.py check-updates` works from any directory without a repository mapping, GitHub CLI or account login. It reads public stable Release metadata and reports installed/reported versions and an advisory link. It does not invoke Skills CLI, install anything, alter readiness or write project/task/setup-checkpoint files. `--offline` skips the request and leaves the latest version unknown. README examples keep installation/update commands explicit and no longer present `npx skills check` as a guaranteed read-only inspection.

The anonymous worker has a three-second process deadline, covering DNS, connection and response reads. It validates stable numeric versions and canonical release links, discards release prose/assets and never follows redirects. On API quota failure it can inspect one HEAD redirect from the canonical [latest-release link](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases) within that deadline. The [release API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release) supports public unauthenticated reads. No credential-store lookup, persistent cache, retry loop or business mapping/task data is involved.

Plugin release discovery does not download a new sync compatibility catalog. Only a separately authorized plugin/skill update refreshes that catalog. A newer plugin alone does not justify a business script upgrade PR or changing account authorization.

## Verification

Regressions cover anonymous requests, source/version/link validation, quota fallback, ignored release instructions/assets, bounded responses, HTTP/network failures and real stalled-process termination. New manual-entry coverage checks repository/account independence, offline/help behavior and unchanged project/checkpoint files. Daily Actions/native progress is guarded against plugin-version requests; existing bundle compatibility regressions remain in place.

The final frozen candidate passed **304 Python tests**, including **24 added regressions**, **23 npm tests**, **31 eval-corpus structure cases**, generation drift/package validation across **67 Markdown files**, and the offline demo. Its 31-file plugin payload remained unchanged through verification.

Actual tarball/native Codex installation validated **37 packed files / 31 plugin files**, all three enabled native skills, fresh/repeated/check/cache-removal behavior and retained local sources. Skills CLI 1.7.4 passed project/global and individual skill installation, repeat/removal and preserved synthetic MCP/settings/auth. The four-agent file-install matrix passed. Native discovery and MCP configuration readback passed for Codex, Claude Code and OpenCode; Cursor configuration readback passed, while native skill discovery remained blocked by login.

The actual manual CLI ran with an empty working directory and empty home, with no Git/GitHub CLI available in PATH. It identified public stable version 0.10.2 in about 0.77 seconds; offline mode returned unknown without network. Both empty directories stayed empty. Tests separately verify the newer-version reminder and network/timeout paths without installing anything. Protected real-profile metadata, business mappings/checkpoints/task records and primary checkout state matched the preservation snapshot; the real installed 30-file plugin remains unchanged.

Raw logs and original missing-command regression evidence remain private. Earlier automatic-detection candidate evidence is superseded by this manual-only scope.

## Limits

This optional command discovers GitHub's designated stable Release, not unreleased commits, per-skill folder changes or prereleases. Anonymous requests can fail or be rate-limited; unknown is not proof that no update exists. There is no scheduler or background discovery; the command runs only when requested.

Fresh model-driven evaluation and new OAuth flows are separate from helper regressions, corpus validation and isolated loading. Cursor native skill discovery, non-Codex native clients outside macOS, GUI/cloud business flows and Skills CLI automatic-update tracking remain unverified. Public installation of this unpublished candidate and remote CI are not claimed.
