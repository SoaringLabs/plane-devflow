# Plane DevFlow 0.11.0 validation

Plugin 0.11.0 and its three standalone skills release the accepted first-project onboarding changes from PR #2. The independently versioned GitHub synchronization bundle remains 0.10.1. Its runtime scripts, generated workflow and compatibility catalog are unchanged. Existing mappings, authorization, state ownership, completion policy and local finalization require no migration.

## Behavior

First-project setup can start from an empty directory, inspect prerequisites, propose one preparation plan and advance through repository/account/project/synchronization steps. Human account consent, credential transfer and merge authorization remain separate handoffs. Bootstrap checks do not create the target directory or contact services.

Recovery prompts carry the target and mapping identity but grant no authorization. Resumption rechecks current resources and recovers original user decisions. First-version planning starts with a chat-only draft; saving a plan does not create tasks or authorize a remote write. Reconciliation checks current complete project snapshots, partial creation and conflicting items before proposing remaining operations.

## Release checks

The versioned release payload passed the following local macOS checks:

- Python 3.14 full suite: **357 passed**; Node.js installer/credential-isolation suite: **23 passed**.
- Deterministic generation check for all three standalone skills, package/resource validation across **86 repository Markdown files**, eval-corpus structure validation for **39 scenarios**, diff whitespace checks and the offline demo passed.
- Actual isolated tarball installation passed: **43 packed files**, including **37 plugin files**, native loading of all three qualified Codex skills, fresh/repeat/check behavior, cache removal and preservation of an existing local source.
- Actual Skills CLI **1.7.4** checks passed: global/project/individual-skill installation, repeated installation, changed-source reinstallation, source/cache removal, self-contained helper startup, MCP metadata parsing and Codex native discovery/configuration readback. OAuth and transport probes were not performed.
- The four-client file installation matrix passed for Codex, Claude Code, Cursor and OpenCode, including all three payload/helper comparisons and preservation of synthetic configuration/authentication and business mappings. Only the Codex native inspector ran in this local matrix.
- The package file list and new publication text were reviewed. Private live-test identities and links are omitted. Sync runtime, workflow generation and compatibility-catalog bytes match the accepted pre-release source.

Exact release-commit source/tag CI, public GitHub installation and local Codex update readbacks are reported in the published Release after completion.

## Accepted candidate and live evidence

The [candidate validation](validation-first-project.md) retains the original 357-test Python result, 23-test Node result, isolated installation checks and nine fresh-session decision checks. The nine decisions passed with emulated discovery before a Python 3.10 quoting correction; workflow documents were byte-identical after that correction. The accepted final candidate passed all ten jobs in [cross-platform CI](https://github.com/SoaringLabs/plane-devflow/actions/runs/39567371238), including Python 3.10/3.14 and installer/skills checks on macOS, Linux and Windows. These historical results are distinct from this version's release-payload checks.

A disposable private project exercised the installed candidate's empty-directory setup, existing GitHub/Plane connections, private repository and Plane project creation, association, setup PR preparation and a human-operated runner-credential handoff. Read-only resumption reused the existing objects and PR. A first-version sample produced three chat-only tasks without saving or creating that batch.

After the user authorized the setup PR merge, its trusted-default-commit connection check passed. A separately identified acceptance task and documentation-only PR exercised opened, edited and closed events. All three Actions runs reported successful synchronization with no state change. Plane readback confirmed one lifecycle comment with the same ID, updated title and final closed phase; the task state and manual completion policy remained unchanged. The test PR was closed without merging. Private identities, object IDs and Actions links are intentionally unpublished.

## Limits

- The live environment already had tools, plugin discovery, account connections and a saved credential. This does not certify fresh-machine installers, new account signup, browser OAuth or every host UI.
- The three-item first-version batch was drafted only. Real batch creation, lost-response recovery and external-correlation readback for that planning flow remain unverified. Deterministic fixtures cover reconciliation but cannot establish server-side uniqueness; concurrent creators can race.
- Live PR writeback covered opened, edited and closed events in Actions/basic mode. It did not cover merged, draft or reopened events, native-provider behavior or legacy automatic state transitions.
- Candidate model decisions used synthetic discovery and a CLI-default model, not a pinned release model. No new model evaluation is implied by the version change.
- The release installation matrix checks files/helpers and preservation across Codex, Claude Code, Cursor and OpenCode. Only the Codex native inspector ran in this local release matrix; the other three native inspectors were not run. Package checks do not establish Skills CLI automatic-update tracking, authenticated client behavior, self-hosted deployments or fresh end-to-end behavior in every client.
- Distribution remains GitHub/Skills CLI plus local Codex installation. This release does not publish a project-owned npm package or upgrade copied business-repository synchronization files.
