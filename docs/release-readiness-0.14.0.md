# v0.14.0 release preparation

Date: 2026-10-22. Status: preparation only. No tag, GitHub Release, npm publication, stable-channel promotion or business-project migration is authorized by this record.

The implementation base is public main commit `650a116b6e8ec64075d5ac0215a508448fc8f481`, merged through [PR #11](https://github.com/SoaringLabs/plane-devflow/pull/11). Preparation changes are documentation only. Keep the changelog entry marked **Unreleased** until cutting the separately authorized release; use the actual release date then.

## Publication contents and language

- Product version: **0.14.0**, from `VERSION`, shared by plugin/npm metadata, generated skills, local helpers and the public Action.
- Public skill inventory: `plane-setup`, `plane-start`, `plane-deliver`.
- Supported data contracts: mapping schemas **1/2**, PR binding protocol **1**. The historical 0.10.1 copied bundle is a compatibility adapter, not a separate new release.
- Release title/body draft: [English release notes](release-notes-0.14.0.md). The [changelog](../CHANGELOG.md) is English, following [release language policy](../PUBLISHING.md#release-language).
- Required release asset: `plane-devflow-release.json`, generated from the exact final committed source. Candidate manifests remain outside tracked source and use `channel=candidate`; they are not upload-ready stable manifests.
- Skills CLI distribution uses an explicitly promoted `stable` branch. The optional npm installer is tested locally; publishing npm is a separate decision and is not needed for this release's Skills CLI path.
- Public notes summarize private sandbox results without test repository/project/task IDs, private run URLs, credential material or personal filesystem paths. Raw live evidence remains unpublished.

## Existing evidence, read back during preparation

The merged implementation's [main CI run](https://github.com/SoaringLabs/plane-devflow/actions/runs/39731300452) completed successfully at the exact base commit: **10/10 jobs**. It includes Python 3.10/3.14, Node installer checks and Linux/macOS/Windows installation matrices. This is evidence for the implementation commit, not a tag or a later preparation commit's CI.

The [implementation validation](validation-0.14.0.md) retains the initial 470-test baseline. The [review record](review-0.14.0.md) retains the subsequent **500 Python / 23 Node** pass, actual isolated project/global Skills CLI upgrades, npm tarball/native Codex installation and four-host file/helper checks. Historical failures and limitations are preserved.

Subsequent isolated live validation used the public implementation commit and a private disposable repository with one separately approved Plane task:

- Verified the known legacy baseline, then ran the actual upgrade coordinator through plan, stage, project diff, isolated project-scope installation and PR creation. A retry reused the same upgrade PR. Merging it activated the shared Action without changing the mapping.
- Executed the public Action on GitHub and verified real Plane lifecycle updates for opened, edited, synchronize, ready-for-review, converted-to-draft, close, reopen and merge events. One lifecycle comment was updated throughout; task state and completion remained unchanged.
- Replayed an old opened event after the PR state changed; it read current GitHub state without reverting the comment or creating a duplicate.
- Supplied an invalid PR-head mapping and a sentinel script; synchronization still used trusted configuration and pinned public code. Those fixtures were restored before merging. Non-default-branch manual dispatch skipped its job.
- Generated a local reverse rollback diff and compared the original three files byte for byte; no remote rollback or standalone local downgrade was performed.
- Verified a fresh read-only connection run on the final test default-branch commit. The final upgrade check retained `verification_pending`: live connection passed, but no formal 0.14.0 Release manifest exists yet. No candidate was presented as a formal release.

## Current preparation checks

Fresh checks on the preparation tree used macOS arm64, Python 3.14.3, Node.js 24.15.0 and actual Skills CLI 1.7.4. Runtime, canonical skills and generated payloads are unchanged from the implementation commit.

| Check | Observed result |
| --- | --- |
| Development dependencies | Existing virtual environment has pinned PyYAML 6.0.3; `npm ci --ignore-scripts` passed |
| Full Python suite | **500 passed** in 418.671 seconds |
| Node installer/credential isolation unit suite | **23 passed**, no failures or skips |
| Version / standalone generation | Both `--check` commands passed without drift |
| Package, resources and documentation links | Passed for canonical/generated payloads and 99 repository Markdown files |
| Decision / execution corpus validation | **48 / 5** structurally valid; no model execution |
| Offline demo | Passed; lifecycle replay retained one comment |
| Actual npm tarball installation | **53 packed files / 46 plugin files**; fresh, repeat, cache removal, check mode, retained-source and native Codex discovery passed |
| Actual Skills CLI installation | Project/global coordinator, individual/selected skills, repeat, changed-source refresh, fixed-commit fixture, removal and Codex native discovery passed |
| Four-host compatibility matrix | Project/global/repeat/removal and all payload/helper checks passed for Codex, Claude Code, Cursor and OpenCode; native discovery/configuration passed for Codex, other native clients not run |
| Real-profile protection | Protected original-profile metadata unchanged in each actual installation suite; credentials not copied into fixtures |
| Package inventory / public evidence audit | Exact plugin inventory present; development/private artifacts excluded from the npm package; 313 source/preparation files scanned without references to private live-test identities or personal paths |
| Language and body portability | Changelog and complete draft title/body reviewed in English; Release-body links use the planned version tag rather than relative paths |
| Whitespace and scope | Passed; eight documentation paths only, no runtime or generated-payload changes |

During documentation editing, package validation caught a draft installation-guide link to a nonexistent anchor. It was corrected to the existing `#validation-scope` heading and validation passed again. The original failure/correction is retained in private preflight evidence; it did not require a runtime change.

The candidate manifest is generated from the local preparation commit and verified against a clean export after this record is committed. Its full source identity, file count and checksum are recorded outside versioned source to avoid self-reference. The manifest stays `channel=candidate`; the final source cut requires regeneration. Raw test output, installation fixtures, prepared title/body and manifest remain in ignored local evidence, outside the public package.

These results do not establish remote CI for the new preparation commit, publication or public stable installation. The previous 10/10 remote result applies to the exact implementation base identified above.

## Authorized publication sequence — not executed

1. Review this preparation diff and the complete English title/body. Replace the Unreleased changelog heading with the actual version/date as part of the final source cut. Commit those reviewed source changes and run affected document/package checks. Record the resulting full commit; do not tag an earlier implementation or preparation commit accidentally.
2. Under publication authorization, deliver the reviewed final source through the normal PR/merge process, then confirm main's actual commit and all required CI jobs. Reconcile any intervening changes before cutting a release. No push, PR or merge is performed by this preparation.
3. Generate the final manifest from that full committed main SHA using `scripts/release_manifest.py --commit FULL_RELEASE_SHA --output /tmp/plane-devflow-release.json` without `--candidate`. Export that commit to a clean source directory and run `product_release.verify_source` against every manifest path. This local `channel=stable` file is still only a prepared asset until the matching formal Release is published.
4. Confirm `v0.14.0` is unused. Under release authorization, create the version tag at the exact verified commit and publish the reviewed English notes with the manifest asset. Never move a historical tag or derive identity from `target_commitish` alone. Read back the title/body, tag target, asset name and bytes; resolve the release through `product_release.resolve('0.14.0')` and compare the full source payload. Verify tag CI separately.
5. Only after formal Release identity and payload verification, and under stable-promotion authorization, promote `stable` to that same commit without overwriting divergent history. Read back its SHA and run the exact public README command with a fresh cache, isolated profile and credential isolation. Test project/global scope, all three payloads and helper startup. Read back the resolved formal version; do not reuse candidate-only success as this evidence.
6. In the isolated test repository, exercise the published manifest/pin and final verification path, with fresh connection and actual task-bound writeback readback. Confirm `verification_pending` clears only when formal identity and all required activation checks are satisfied. Keep any business migration separate.

If publication stops midway, report the actual tag/Release/asset/channel states. Do not promote `stable` after a partial publication or claim a public installation succeeded before executing it. An npm publish or Marketplace listing is not part of this sequence.

## Remaining limits

No formal release-asset download, stable-channel activation/public installation or post-publication upgrade is claimed. No new model evaluation, real host plugin refresh or additional native-host discovery is performed by this documentation preparation. Existing private test resources are retained for audit; no new business repository or credential changes are needed.
