# Plane DevFlow 0.15.1 validation

Date: 2026-10-31. This record covers implementation and local release-preparation evidence. Final release-source CI, tag, manifest, stable-channel promotion and user-installation readbacks are separate publication results recorded with the GitHub Release.

## Scope and compatibility

The release requires English prose in the complete titles/subjects and bodies of development commits, PRs and final squash/merge commits. Plane tasks, progress reports and conversation retain the user's language. Generated GitHub report translation preserves task IDs, binding/evidence markers, verification facts and limitations. Merge messages are explicitly supplied and read back; published history is not rewritten automatically.

The change is local skill guidance. Synchronization implementation, mapping schemas 1/2, PR binding protocol 1, credentials and state ownership remain compatible. Existing project Action pins do not need a version-only update. Projects using independent local skill installations must refresh those copies separately; a global plugin refresh does not modify project workflows.

## Executed checks

Local environment: macOS arm64, Python 3.14.3, Node.js 24.15.0 and Codex CLI 0.165.0.

- The merged implementation passed 528 Python tests, 23 Node installer/credential-isolation tests and all required GitHub checks. Independent standards and specification reviews reported no findings.
- The 0.15.1 release preparation passed 23 Node tests, actual Skills CLI 1.7.4 installation/native-discovery checks, and actual npm-tarball/native-plugin integration checks. Tests preserved original user-profile metadata.
- Version consistency, standalone generation consistency, all 50 decision-fixture schemas, all 5 execution-fixture schemas and the offline workflow demo passed. Fixture schema checks do not execute models.
- The npm dry-run contained 57 packaged files, including the new writing reference, and excluded development fixtures, caches and private evidence. No npm publication was performed.
- Two isolated artifact-producing forward checks verified complete English GitHub prose, Chinese Plane reports, explicit squash messages and retained verification limits. Translated report metadata also passed the production evidence and task-binding checks.

The first local release-preparation full run overlapped assembly of this new validation document: 528 tests ran, with 4 failures and 2 errors, all caused by package fixtures copying the changelog before its referenced document existed. The other 522 tests passed. After the complete source was committed, all 21 package-validation tests passed on retry. No runtime change or test waiver was needed; the original failed run is retained. Both Python 3.10/3.14 CI runs passed on that complete preparation commit. Final release-head checks are verified separately before publication.

## Fresh-session comparison

The same harness, action catalog and fixtures ran DELIVER-13 and DELIVER-14 once each against the published 0.15.0 baseline and the 0.15.1 candidate. Baseline scored 0/2; candidate scored 2/2; neither produced a forbidden decision. Traces read the selected skill and relevant references, including the candidate's writing policy. Baseline decisions did not establish the required complete English-message review.

| Input | SHA-256 |
| --- | --- |
| Baseline plugin payload | `a3415eb68f89de1880b60a1d0115723ba8455783223ec074400bf1893cd6f0b2` |
| Candidate plugin payload | `7df037edb409cf0dad3bc7694cc8b19749ad4b0a76e6521ce8bf31f4b80a7600` |
| Rubric | `3178a3a81eeaa7945cfe3d9f22268eab8325658faacfb938fa876b04d471142c` |
| Harness | `bb444e8e2b62704670f4a134c3a54f3ab1722721ec0493e7b9b354a083de1e7c` |

The CLI used its default model without an override. User configuration, rules, plugins, memories and hooks were disabled; discovery was emulated with the supplied catalog. Raw traces remain private. One repetition is a smoke comparison, not a stability estimate or proof of live tool effects.

## Limits

Language review remains agent-guided rather than enforced by an automatic translator or language detector. The model comparison does not perform real GitHub merges or Plane writes. Fresh authenticated execution on Claude Code, Cursor and OpenCode was not tested. Existing business workflows and independent host installations are not migrated by this release.
