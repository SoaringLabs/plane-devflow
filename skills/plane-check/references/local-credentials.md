# Remember and reuse a Plane PAT on this computer

Read this when the user wants to remember a PAT, reuse one for another repository,
replace a saved credential, or forget its local copy. This is an optional Actions
credential path. Native integration needs no runner PAT.

## Select the account and inspect

For Actions onboarding, first check the repository's GitHub Secret metadata.
An existing Secret needs verification, not a new PAT; unknown metadata needs
diagnosis before replacement. An explicit local-only create-and-save request
uses the automatic branch below without requiring GitHub access.

For a missing Secret, obtain the verified **Plane** account ID or email from live
account context or the user. Do not substitute the GitHub login or infer an
account from repository ownership. Prefer a stable account ID; reuse the same
identifier on subsequent projects. Never ask for a PAT in chat.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py credential-guide \
  --repo /absolute/repo --step local --account PLANE_ACCOUNT_ID
```

Lookup is scoped to Plane API origin, workspace and account, across all project
repositories on this computer. It returns presence or unknown and never returns
the token. macOS uses Keychain through Security.framework; Windows uses Credential
Manager through Win32 APIs. Windows has no metadata-only credential read API; its
presence probe releases the native buffer without exposing the blob to the agent.
No ordinary files, skill directories or project configs hold the token.

`saved` does not establish validity or project access. `unavailable` is unknown,
not absence: explain locked/denied/unsupported storage and offer manual input.
No native vault is accessed merely by installing skills or checking capabilities.

## Automatic creation from Plane App

Use only when the user explicitly requests creating a PAT **and** saving it to
this computer's Keychain. Choosing Actions or finding a missing Secret is not
that authorization. Plans and capability checks never read the App session.

Supported: macOS, Plane Cloud, the known Plane App cookie format. Confirm the
Plane account ID/email (consistent with existing local scope), workspace/project
and an explicit expiry. A PAT inherits the owner's full permissions. Reuse the
user's choices and authorization; when complete the agent runs the helper without
terminal input, a browser button, or DevTools.

```sh
python3 /absolute/plugin/scripts/plane_workflow.py credential-create \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --expires-at ISO8601_EXPIRY
```

The plan returns an operation UUID, mapping digest, PAT label, destination and
exact `apply_command`. Check these against user authorization, then execute that
command with `--apply`. Retain the operation ID, expiry, mapping digest and
replacement choice on retries. `--replace` needs explicit local replacement
intent. Existing credentials are preserved unless replacement was requested.

The helper reads only Cloud auth cookies through read-only SQLite, confirms the
session account, creates the PAT, and saves it first to an operation-specific
pending Keychain entry. After verifying the server-applied expiry, identity and
mapped project access, it promotes to the normal account/workspace entry and
verifies readback. A failed promotion retains the pending native-store copy.
Encrypted/unknown cookie formats stop safely; no implicit decryption is attempted.
Native calls fail rather than opening an unlock prompt. There is no plaintext,
clipboard, console, command-argument, environment-variable or HTTP-redirect bridge.

For `login_required`, say: “请先打开 Plane App，登录对应账户；完成后告诉我继续。”
After login resume the same authorized operation. App-running state is not proof
of login. Account mismatch, 403, network failure, unreadable session storage and
Keychain denial require their own diagnosis, not another login/token by default.

Metadata receipts and a shared per-account/workspace process lock live in the
user's `Library/Application Support/Plane DevFlow/credential-operations`. They
contain operation state, mapping binding, PAT ID and expiry, never credentials.
Receipts are progress, not authorization; check current user intent on resume.

| Result | Continue |
| --- | --- |
| `verified` | Local save, readback, identity/project checks passed. Use `credential-guide --step local --account PLANE_ACCOUNT_ID`; GitHub transfer stays separate and human-operated. Do not record `pat-ready` as though the user copied a token. |
| `already_completed` | Historical success only; timestamp does not prove current validity or GitHub readiness. |
| `login_required` / `account_mismatch` | Sign in or switch to the intended account, then resume the same operation. |
| `creation_unconfirmed` | The same operation checks Cloud metadata; it never blindly replays an ambiguous POST. |
| `created_without_local_copy` | Report this PAT's ID/label for scoped recovery. New creation, remote revocation or receipt reset needs explicit intent. |
| `keychain_unavailable` | Unlock/repair access and resume; preserve pending credentials and old entries. |
| `pending_cleanup=retry_required` | Target succeeded, but this operation's pending local copy still needs cleanup; preserve unrelated entries. |

Unfinished operations block another creation for that same scope. Known,
server-verified expired operations do not block a separately authorized new one.
Old PAT revocation, other-key cleanup and GitHub Secret updates are separate.
Cloud/Keychain checks never establish Actions connection or real event writeback.

The cookie schema and web PAT endpoint are internal compatibility boundaries;
unknown formats or responses stop and keep manual entry available. See
[Plane authentication](https://developers.plane.so/api-reference/v2/authentication)
and the [web PAT service](https://github.com/makeplane/plane/blob/preview/packages/services/src/developer/api-token.service.ts).

## Human-operated entry and reuse

Present these commands in a terminal visible to and operated by the user. An agent
may inspect metadata or prepare a command, but must not fill PAT input or simulate
the human confirmation. Do not run a secret-print command, read clipboard contents,
or ask for the token via a tool questionnaire. The helper fails if hidden input
is unavailable instead of falling back to visible input.

To save a PAT locally without configuring GitHub, plan the operation first, then
let the user run it with `--apply` and enter the PAT through hidden input:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py credential-store \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --action remember
python3 /absolute/plugin/scripts/plane_workflow.py credential-store \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --action remember --apply
```

When a saved credential exists, show the exact destination repository and offer
reuse. The human runs:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py set-secret \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --use-saved
```

The command asks the user to type the destination `OWNER/REPO` before loading the
credential. It rechecks the mapping/origin, then sends the PAT directly to `gh`
through stdin. It does not place the token in arguments, output or temporary files.

For a first setup, the user can instead opt in to remembering hidden input while
configuring the repository:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py set-secret \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --remember
```

Without either flag, the existing `set-secret` manual-input path persists no
local copy. If no suitable PAT exists, follow [credential creation](credentials.md).
Browser-only users can keep the manual GitHub Secret form route.

After the human command, read GitHub Secret metadata and run the trusted connection
check as setup describes. Presence of a local entry or a successful upload does
not establish readiness. If GitHub fails after local saving, retain the local
entry and resume only the failed upload; never generate another PAT automatically.

## Replace, forget and recover

Existing local or remote credentials are preserved unless the user explicitly
chooses replacement; only then add `--replace` to the appropriate human command.
For `set-secret --remember --replace`, explain that both local and remote copies
may be replaced. Cancellation leaves both unchanged. A failed remote operation
does not roll back a newly remembered local entry.

To remove only the selected local entry, plan/apply:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py credential-store \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --action forget
python3 /absolute/plugin/scripts/plane_workflow.py credential-store \
  --repo /absolute/repo --account PLANE_ACCOUNT_ID --action forget --apply
```

The human confirms the account in the terminal. This does not revoke the PAT in
Plane or remove GitHub Secrets. Uninstalling/updating skills also leaves the
system credential entry alone. Retention is opt-in and applies to this computer;
no cross-device synchronization, export, or plaintext fallback is provided.
Other platforms retain manual entry. Expiry, lost account access and storage
errors require diagnosis; a failed connection never grants replacement authority.

Native adapter contracts are covered by synthetic tests. Those tests do not prove
real Keychain unlock/ACL behavior, Windows logon-session behavior, or live GitHub
write access; report actual platform/service verification separately.
