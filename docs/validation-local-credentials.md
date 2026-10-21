# Local runner credential validation

This source change adds opt-in system storage for the Actions runner PAT. A missing
repository Secret now routes through existing/local credential checks before PAT
creation. The lookup scope is Plane API origin, workspace and account; repositories
and projects do not partition the saved credential. Native integration still skips
runner credentials. This record does not imply a version tag or public Release.

## Deterministic coverage

The credential tests cover account/workspace/instance isolation, cross-project
reuse, metadata-only inspection, unsupported or locked storage, explicit overwrite
protection, hidden-input cancellation, changed repository mappings and concurrent
Secret updates. Uploads use GitHub CLI stdin; command arguments, structured results
and ordinary files contain no PAT. Uncertain GitHub writes retain an opted-in local
copy for recovery. Both native API adapters have simulated contract coverage.

## Native macOS evidence

The production macOS Keychain adapter passed saving a unique synthetic entry,
inspection from another repository/project, reading through the production upload
helper, rejecting an implicit replacement, explicit replacement and deletion.
Cleanup confirmed the synthetic entry was absent. Human input and the GitHub sink
were simulated in this test; existing real credentials were not read.

To repeat this explicit native smoke test on macOS:

```sh
.venv/bin/python scripts/native_credentials_smoke.py --run
```

Ordinary test discovery does not run this command. The test owns only its unique
synthetic entry, cleans it up, and makes no GitHub network call.

## Human-operated live GitHub evidence

A separate, private acceptance run used human hidden PAT input and the production
helpers: remember in Keychain, inspect from a second temporary project mapping,
read the saved credential and upload `PLANE_API_KEY` to an authorized repository.
Fresh GitHub Secret metadata confirmed the upload. The test then deleted its new
repository Secret and verified absence. Existing repository code, workflows and
formal project mappings were unchanged; the project fixtures were synthetic.

The user chose to retain the local credential for future use and cancelled the
final forget prompt. The one-off harness therefore recorded an incomplete cleanup
as a failure; the preceding storage/reuse/upload checks passed. This is not a claim
that the entire cleanup harness passed. Account/repository identifiers, local paths,
PAT values and raw private evidence are intentionally omitted from this record.

## Limits

- Windows native credential storage was not tested on a Windows device; the user
  explicitly scoped native testing to macOS. Simulated adapter tests are separate.
- Secret presence/upload does not establish PAT validity, project access or a ready
  Actions integration. No live Plane API or PR-event synchronization was tested.
- No cross-device credential synchronization or plaintext fallback is provided.
- No new model-driven decision evaluation was run; evaluation fixtures have
  structural validation only.
