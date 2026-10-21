# Plane DevFlow 0.12.0 validation

Validated on macOS with Python 3.14.3 and Node.js 24.15.0, 2026-10-21.
The accepted implementation was first tested as an unpublished candidate, then installed locally.
Release-payload checks and publication readbacks are recorded separately below.

## Behavior

An explicitly authorized `credential-create` plan binds the verified account,
mapping digest, expiry and operation UUID. Apply needs no terminal input or
desktop automation. It authenticates using the known Plane App Cloud cookie
format, creates one PAT, saves an operation-specific pending Keychain copy,
verifies identity/project/expiry, promotes to the normal scoped entry, and checks
readback. Existing entries need explicit replacement intent. Unknown creation
outcomes reconcile metadata instead of replaying a POST. Login, permissions,
network, session-format, progress and native-store problems retain distinct
outcomes. Only metadata enters output and receipts.

## Executed checks

| Check | Result |
| --- | --- |
| Full Python regression suite | 388 tests passed |
| Installer and credential-isolation Node tests | 23 tests passed |
| Package/Markdown and extracted-payload validation | Passed |
| Generated standalone skills | Three generated; `--check` reports no drift |
| Skill Creator entrypoint validation | Passed |
| Evaluation dataset validation | 43 cases valid, including four new credential authorization/recovery cases |
| Offline workflow demo | Passed |
| `git diff --check` | Passed |
| New helper, real desktop session, read-only Cloud identity request | Authenticated account matched; no PAT creation or Keychain write |
| Integrated CLI, real Cloud PAT creation and normal scoped Keychain destination | Passed with a 15-minute PAT, replacement disabled, and no mocks/overrides or UI interaction |
| Independent process: saved PAT identity/project access, Cloud metadata and expiry | Passed; exactly one matching Cloud PAT, pending entry absent, pre-existing ID-scoped entry still present |
| Same operation executed again | `already_completed`, same PAT ID; no duplicate creation |
| Native no-UI Keychain smoke | Synthetic save/read/replace/delete passed; owned test entries verified absent |
| Automatic controller with real Keychain and synthetic Cloud/session | Passed; normal/pending entries cleaned up |

Reproduce the main checks using the development environment from
[CONTRIBUTING.md](../CONTRIBUTING.md). The additional native smoke is explicit:

```sh
.venv/bin/python scripts/native_credentials_smoke.py --run --plane-app
```

The `--plane-app` smoke uses a unique synthetic scope, actual Security.framework calls with
interaction disabled, and synthetic session/HTTP responses. It never needs a
real PAT or creates a Cloud credential. The regular test suite uses synthetic
credentials only. Existing HTTP-error fixtures in other modules can emit
ResourceWarnings; those warnings were not hidden. The new Cloud client closes
error responses and tests that finalizer warnings cannot disclose raw errors.

## Explicit live validation

After separate user authorization, the candidate's unmodified `credential-create`
CLI executed its returned plan/apply command against a real Plane App session,
Plane Cloud and Security.framework. No session/client/vault mocks or destination
overrides were used. The controller, CLI and native adapter file hashes stayed
unchanged during execution. A 15-minute PAT was created and saved to a previously
empty normal account-scoped destination without `--replace`.

A separate process confirmed the saved entry, read the PAT only in memory,
verified its account and mapped project access, checked its exact Cloud ID/label
and server-applied expiry, and confirmed the pending entry was removed. Repeating
the same authorized operation returned `already_completed` with the same PAT ID.
The pre-existing ID-scoped credential remained present; GitHub Secrets were not
changed. Private metadata evidence is kept outside the repository; no credential
or personal account/project identifiers enter this report.

## Versioned release checks

The plugin, npm-compatible bundle metadata and all three standalone distributions
are 0.12.0. The independently versioned synchronization bundle remains 0.10.1;
its shipped scripts/workflow are byte-for-byte unchanged.

- All 388 Python tests passed on the versioned payload (166.238 seconds).
- 23 Node tests passed after a clean dependency install.
- The exact local tarball contains 44 files, including 38 plugin files. Isolated
  fresh/repeat/check installation, cache removal, retained-source behavior and
  all three native Codex skill loads passed.
- Skills CLI 1.7.4 global/project/individual-skill installation, reinstallation,
  source/cache removal and Codex native discovery passed.
- The four-client file-installation matrix passed for Codex, Claude Code, Cursor
  and OpenCode, preserving synthetic configuration and business mappings.
  Only Codex native inspection ran; other native clients remain unverified.
- Generated skills, 87 Markdown resources, 43 eval scenarios, the offline demo,
  diff checks and native synthetic Keychain save/read/replace/delete checks passed.

### Fresh-session credential decisions

Four affected scenarios ran once with Codex CLI 0.163.0 using its default model
(no model override), an explicit skill catalog, synthetic fixtures and read-only
document access. Trace review confirmed all four read the relevant skill and
credential references and executed only document reads. These checks do not
perform native discovery, network calls or credential operations.

Initial scoring passed 2/4, with zero forbidden decisions. Two redundant rubric
labels caused failures: CRED-AUTO-01 omitted a separate `inspect_auth` label even
though the create/verify decisions covered the helper's mandatory identity check;
CRED-AUTO-02 omitted `report_partial` while explicitly stopping at login and
retaining the original operation. The reviewed rubric retains creation/verification
requirements for the first case and `prompt_plane_login` for the second. All
forbidden decisions and human review criteria remain unchanged. Rescoring the
same decisions passes 4/4; original scores and traces are preserved privately.
The initial runner summary captured the rubric hash at completion after that
edit, so a separate private audit records the actual run-start snapshot digest.
A separate stable-rubric fresh run passed 4/4, with zero forbidden decisions,
under the same CLI/default-model settings. Each scenario ran once. The runtime
payload digest was `a5999fec4af4e0ccbc07967824e73de89eb3bf6b284bc830dfa6da404eb65557`;
the initial rubric snapshot digest was
`fb271401d8dd48c21c1c5ebc73b526f2d0970fe23af11403cee2c2833b2d6245`,
and the reviewed rubric digest was
`c6ad77a2be2c17f4f6c4eb3de9e2fda295ec57af61e821fe5777707c850bd305`.

## Test credential cleanup

After explicit cleanup authorization, all three PATs created during the Cloud/Keychain
verification stages and their three corresponding Keychain entries were deleted.
Fresh Cloud metadata and native metadata-only Keychain queries confirmed their
absence. Non-target PAT metadata and the pre-existing scoped Keychain entry
remained unchanged. Cleanup did not read credential values or modify GitHub
Secrets. Private IDs, labels and audit evidence remain unpublished.

## Limits

- Live validation used a previously empty account-scoped destination with
  replacement disabled. It does not validate replacement of an existing real
  credential; that behavior has synthetic/native-smoke coverage.
- Dataset validation is separate from the four synthetic decision checks above;
  neither establishes stability across models, repeated runs or live tool effects.
- macOS/Plane Cloud/known plaintext cookie storage only. Encrypted or unknown
  layouts stop safely; Windows/self-hosted users retain manual entry.
- No dedicated closed-App live test, locked-Keychain UI test, GitHub Secret
  update, Actions dispatch, or real PR-event writeback was performed.
- The desktop cookie schema and web PAT endpoint are private compatibility
  boundaries. A successful test does not promise future upstream stability.
- Release, merge, installation update, old-PAT revocation and unrelated local
  credential cleanup are separate actions.

See [automatic credential creation](../plugins/plane-devflow/references/local-credentials.md#automatic-creation-from-plane-app)
for authorization, recovery and runtime limits.
