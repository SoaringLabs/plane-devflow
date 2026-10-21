# Capabilities and evidence boundaries

This is the current capability inventory. See [0.13.0 validation](validation-0.13.0.md) for the current release checks and retained failures. Historical validation reports retain their original versions, counts, failures and limits. A feature's implementation, deterministic checks, decision scores, native host discovery and real service effects are different kinds of evidence; none implies all the others.

| Capability | Implemented behavior | Evidence to inspect | Limits |
| --- | --- | --- | --- |
| Project setup | Conversational repository/project association, first-project preparation and resumable configuration | [First-project validation](validation-0.11.0.md), setup/configuration regressions | Installing skills does not authenticate an account or activate synchronization |
| First task list | Draft, review, explicitly approved creation; reconcile active and archived tasks after lost replies | [Planning guide](../skills/plane-start/references/task-planning.md), planning tests, [execution evals](../evals/README.md#execute-synthetic-workflows) | No general task/Cycle/Module management; a plan alone creates nothing |
| Task development | Explicit identity, isolated checkout, scope guard, shared local brief/check receipts, base/conflict recovery | [Checkout validation](validation-0.7.0.md), checkout/workspace tests and synthetic execution cases | Same-repository local receipts; semantic diff review remains necessary |
| PR delivery and recovery | One primary bound PR; implementation report, link/comment readback, resume only missing writeback | [Task execution](../skills/plane-deliver/references/task-execution.md), delivery tests and synthetic MCP audit | A successful PR does not establish successful Plane writeback or acceptance |
| Acceptance and completion | Version/criteria-bound declarations, original-human-message checks, exact-head merge gates, separate local handoff | [Receipt validation](validation-0.5.0.md), [handoff validation](validation-0.6.0.md), gate/handoff tests | Stored source fields cannot authenticate consent; a process exit or ready gate grants no authority |
| Sync readiness | Configuration facts, historical connection result, 24-hour evidence age and shared daily metadata cooldown | [Recovery guide](../skills/plane-setup/references/recovery.md), sync-health regressions | Connection success does not prove an actual PR-event run or writeback; expiration allows independent development |
| Task diagnosis | Explicit task's checkout/head, receipt freshness, PR/CI, Plane snapshot, writeback, environment and handoff summary | [Diagnosis guide](../skills/plane-deliver/references/task-diagnostics.md), diagnostic regressions | Default local/cache only; explicit refresh reads GitHub, host MCP supplies Plane facts; no repair/dispatch/writes |
| Agent installation | Self-contained skills for Codex, Claude Code, Cursor and OpenCode; complete Codex plugin alternative | [Compatibility matrix](agent-compatibility.md), isolated installation/native-loading checks | File installation is distinct from native discovery, model execution and authenticated MCP access |
| Local credentials | Optional native macOS/Windows credential stores; explicitly authorized macOS Plane App create-and-save recovery | [Credential validation](validation-0.12.0.md), credential isolation/native adapter checks | The recorded real Cloud/Keychain test is a scoped macOS result; no universal host/session-format support claim |
| Background PR events | Actions runner plus separate PAT, or observed official integration mapping/rules | [Live capability record](plane-github-capability-verification.md), [event fix validation](validation-0.10.1.md) | Historical scoped live evidence; a new installation/connection needs its own checks. No distributed exactly-once guarantee |

New basic mappings record activity and preserve states. Legacy Actions mappings keep their configured state rules; the official integration owns its own transitions. No new state-policy customization is introduced.

## Readiness and diagnosis cadence

Routine Start uses offline local diagnosis and an opt-in daily metadata cache shared across worktrees. Successful and failed probes both start a 24-hour cooldown. Evidence can become stale during that period; it is reported honestly without polling or automatically dispatching a connection test. Explicit setup/revalidation/authorized diagnosis can refresh. An actual PAT connection dispatch is restricted to initial setup, explicit revalidation or authorized diagnosis. Real PR events run independently.

`task-status` is read-only: by default it reads local records and existing cache without a remote request or cache write. `--refresh` is an explicit current GitHub read; no automatic refresh loop is added. A current Plane snapshot comes from the host's MCP read, not helper-managed credentials. Connection verification, observing the actual Actions event and confirming task writeback remain separate facts.

## What a validation result means

| Evidence | Establishes | Does not establish |
| --- | --- | --- |
| Deterministic Python/Node tests | Helper behavior under recorded fixtures; parsing, guards and failure recovery | Model intent understanding or every real service contract |
| Fresh decision session | Routing and selected actions under a synthetic scenario/catalog | Native discovery or actual business effects |
| Synthetic execution session | Inspected file/Git/simulated-service effects through actual model tool execution | Production OAuth, real Plane/GitHub contracts or cross-host stability |
| Isolated install/native inspection | Payload installation and the native inspector actually run | Browser consent, model-driven access or other clients' native UI |
| Scoped real service observation | The named account/project/event/operation at its recorded time | Permanent readiness or every host/deployment |

The evaluation runner freezes payload/rubric/harness inputs before sessions. Failed, timed-out and usage-limited runs stay visible; an unrun case is unverified. A single repetition is a smoke check, not a reliability estimate. Raw traces remain private. Release-specific results are recorded separately from this inventory.

## Scope ownership

Local cross-chat recovery uses task bindings and receipts when the host supplies trusted conversation context. Cross-machine conversation/session transfer belongs to the host agent or its cloud service, rather than a missing Plane DevFlow capability. Multiple hosts and automatic credential adapters need ongoing compatibility checks when dependencies change; this release does not add a new authentication platform.

General task/Cycle/Module management, custom status rules, multiple-primary-PR aggregation, a background reconciliation service, full self-hosted Plane and GitHub Enterprise integrations remain outside scope. Runtime helpers support Plane Cloud and github.com; configurable test origins do not certify full deployment support.
