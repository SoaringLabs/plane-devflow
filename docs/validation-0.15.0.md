# Plane DevFlow 0.15.0 validation

This record covers source and isolated local validation for the 0.15.0 release candidate. Formal tag, manifest, stable-channel and user-installation readbacks are separate publication results recorded with the GitHub Release.

## Scope

The release adds host-specific defaults for new task branches, saved-branch recovery across serial agent changes and simple execution IDs. Existing fixed prefixes remain explicit project policy. Configuration schemas 1/2, PR binding protocol 1, synchronization behavior, credentials and task-state ownership stay compatible. Existing project Action pins do not need a version-only change to enable these local features.

The in-place continuation regression is covered by real Git tests: after main drops a fixed prefix, the existing task resumes on its original branch using its own checkout configuration. Other configuration differences remain blocked. Tests retain scope, baseline, task evidence and staged, unstaged and untracked changes.

## Executed checks

Local environment: macOS arm64, Python 3.14.3, Node.js 24.15.0 and Codex CLI 0.165.0.

- 528 Python tests passed.
- 23 Node installer and credential-isolation tests passed.
- Version consistency, standalone generation consistency, package validation and `git diff --check` passed.
- All 48 decision fixtures and 5 synthetic execution fixtures passed structural validation; structural validation does not execute a model.
- The offline demo passed without live service calls.
- `npm pack --dry-run --json` listed 56 packaged files and excluded local configuration, caches, private evaluation traces and development artifacts.
- The actual Skills CLI 1.7.4 installation suite passed against an isolated candidate snapshot. Installed payload bytes, all three native Codex skills, repeated installation, fixed-source installation, removal and preservation of unrelated configuration were checked.
- The actual npm tarball/native Codex integration suite passed. Plugin payload hashes matched, all three qualified skills loaded and original user-profile metadata remained unchanged. No npm publication was performed by these tests.

## Fresh-session decision comparison

The same current harness and rubric ran START-02 (new task with dirty primary checkout) and START-03 (resume an existing task) once each against the installed 0.14.1 baseline and candidate 0.15.0 payload. Both scored 2/2 with zero critical failures. Captured command events read the selected skill and relevant workflow references; no business helpers or service writes were executed.

| Input | SHA-256 |
| --- | --- |
| Baseline plugin payload | `6a8a4e53c38ee1ca7eb2acd0a5d6a0eb50873a3feccb5414035a5622860ceec7` |
| Candidate plugin payload | `a3415eb68f89de1880b60a1d0115723ba8455783223ec074400bf1893cd6f0b2` |
| Rubric | `70efc8016505e06c7f6f930e4ef96c2d54b333f04dac0132c5799ef48f8498d5` |
| Harness | `bb444e8e2b62704670f4a134c3a54f3ab1722721ec0493e7b9b354a083de1e7c` |

Codex CLI used its default model without an override. User configuration, rules, plugins, memories and hooks were disabled for each assessment, and discovery was emulated with the supplied skill catalog. Raw traces remain private outside the repository. One repetition is a smoke comparison rather than a reliability estimate.

## Limits

Authenticated Claude Code, Cursor and OpenCode end-to-end task execution was not exercised. The decision comparison does not establish real tool effects, and local native discovery does not establish Plane OAuth or GitHub writeback. Concurrent writers on one task, liveness/takeover logic and cross-machine session transfer remain outside this release. Remote release-source CI and real user installation activation require their own readbacks.
