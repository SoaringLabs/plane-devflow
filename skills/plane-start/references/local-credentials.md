# Remember and reuse a Plane PAT on this computer

Read this when the user wants to remember a PAT, reuse one for another repository,
replace a saved credential, or forget its local copy. This is an optional Actions
credential path. Native integration needs no runner PAT.

## Select the account and inspect

First check the current repository's GitHub Secret metadata. An existing Secret
needs connection verification; it does not require a new PAT. Unknown metadata
requires permission/network diagnosis before replacement.

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
