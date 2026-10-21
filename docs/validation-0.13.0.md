# Plane DevFlow 0.13.0 validation

Validated on macOS with Python 3.14.3, Node.js 24.15.0 and Codex CLI 0.163.0, 2026-10-22. Source CI and publication readbacks are separate from local checks. Historical reports and failed runs retain their original results.

## Behavior and boundaries

Connection evidence expires after 24 hours. Routine metadata probes share a worktree-independent cache; successful and failed attempts both start a 24-hour cooldown. Offline doctor and default task diagnosis make no remote requests. Explicit refresh can bypass cooldown without dispatching a connection workflow. Expiry does not block independently authorized development or real PR events.

`task-status` separates caller/task checkout, head/brief-bound checks, PR/CI, a fresh host-MCP Plane snapshot, declared delivery writeback, acceptance/merge declarations, environment ownership and historical local handoff. Repository-level event observations retain source/time without claiming task binding or writeback. Missing/failed remote facts remain unknown. Diagnosis performs no fetch, cache write, dispatch, repair or business mutation.

The plugin/npm-compatible metadata and three standalone distributions are 0.13.0. The sync bundle remains 0.10.1 byte for byte; config versions 1/2, binding protocol 1 and native/basic/legacy state ownership are unchanged. Session portability belongs to the host agent. No new authentication platform, general task/Cycle/Module management or multi-PR aggregation is added.

## Local checks

| Check | Result |
| --- | --- |
| Full Python regression suite | 430 passed on the final local source (207.407 seconds) |
| Diagnostic regressions | 14 passed, including repeat no-write/no-network behavior, wrong directory, stale declarations, remote failures and event/writeback separation |
| New execution grader/fixture regressions | 12 passed, including injected wrong edits, duplicate creates, missing readback, stale gates, dropped conflict behavior, timeout and usage-limit handling |
| Decision grader regressions | 14 passed, including frozen inputs and narrowly scoped route alternatives |
| Installer and credential-isolation Node tests | 23 passed |
| Package/resources, generated skills and both evaluation datasets | Passed; three generated distributions, 45 decision cases and five execution cases |
| Exact npm-compatible payload | 47 tarball files, including 41 plugin files; no tests/evals, private evidence or bytecode |
| Actual npx installation | Fresh/repeat/check, exact payload comparison, retained source/cache behavior and Codex native loading passed |
| Skills CLI 1.7.4 | Global/project/individual install, repeat/reinstall, source/cache removal, native discovery and MCP-preserving removal passed on a fresh retry |
| Four-agent installation matrix | Codex/Claude Code/Cursor/OpenCode file installation and synthetic-setting preservation passed; only Codex native inspection ran |
| Offline workflow demo and diff check | Passed; no live services called |

The initial local Skills CLI run timed out after 180 seconds in the external removal command with no stdout/stderr. The original evidence is retained as unverified. A new isolated run of the complete installation flow passed; no timeout was extended and no credential isolation was disabled. Authentication files and real profile metadata remained unchanged. No new real OAuth/PAT creation, Plane business writes or production PR-event writeback was tested for this release.

Exact source/tag CI and publication readbacks are separate from the local results above. Development reproduction commands are in [CONTRIBUTING.md](../CONTRIBUTING.md); model execution is separately opt-in in [the evaluation guide](../evals/README.md).

## Model decision evidence

All sessions used the CLI default model without an override, one repetition, synthetic inputs and explicit skill-catalog loading. Inputs were frozen before sessions. These are decision checks, not native discovery or live tool effects.

- Task-2 affected cases: 5/5 passed, zero critical failures. Task-3 affected cases: 4/4 passed, zero critical failures. Earlier 3/4 task-specific scores remain preserved; their reviewed redundant labels are documented in the rubric.
- The complete pre-final-event-display candidate scored **42/45**, with zero forbidden actions. The payload SHA-256 was `79a831cf8799b28ca6e5a8c7beb6b08ef4d3702633ea5fea797c7ba5997544f1`; the rubric SHA-256 was `99f3808060e54f6d483ebc4a608e489fdd1728fc042d57d3357936694e7b8b5c`.
- On the final plugin payload, two diagnosis cases and the three original mismatches were checked separately. The original strict result was **2/5**, with zero forbidden actions. Both diagnosis cases passed. SETUP-02 safely inspected local credentials before manual Secret guidance; ONBOARD-02 supplied the copied resume handoff under an equivalent label; UPDATE-01 read setup's manual-update reference while retaining check-only scope. Command traces contained only document reads, and human criteria were inspected.
- After those runs completed, the reviewed machine projection accepted only the explicit equivalent routes/labels. All forbidden effects and human criteria stayed intact. Separate rescoring produced **45/45** for the original full decisions and **5/5** for the final affected decisions. These are rescored results, not fresh 45-case sessions.
- A new frozen-rubric session for the three calibrated cases passed **3/3**, with zero critical failures. Final payload SHA-256: `555f3191a3cadfd0274aa104b11400b8f2a736242b94531ba4c9f979f6d9ee66`; corrected rubric SHA-256: `d77a08637199580ce20d01e3a62034a1b667909ae8e6dcf48283bc71559fb921`; harness SHA-256: `bb444e8e2b62704670f4a134c3a54f3ab1722721ec0493e7b9b354a083de1e7c`.

Original scores/snapshots were not rewritten. A single repetition is a smoke baseline, not a reliability estimate. Rubric alternatives do not relax actual authorization or prove complete semantic quality.

## Synthetic execution evidence

The five scenarios actually exercised disposable Git repositories/worktrees, a local bare origin, synthetic GitHub CLI and a stdio Plane MCP service. Assertions inspect completed command output, protected files, Git branches/remote refs, service writes/readbacks and receipt state. Final model prose alone cannot pass.

Task-2's final batch passed **5/5** on payload `957565603d686fbb419adb7a1ffe9f7104a2a324da027d407d39782e0bab91a2`. A versioned release candidate passed **5/5** on payload `79a831cf8799b28ca6e5a8c7beb6b08ef4d3702633ea5fea797c7ba5997544f1`. Both ran one repetition. The final event-display patch changes only `scripts/task_diagnostics.py` and its diagnosis reference relative to that release snapshot; affected diagnosis decisions and 14 deterministic regressions cover the final change. Do not label the earlier execution snapshot as the final payload.

The execution rubric SHA-256 was `230973dc0fc21163e1a0374199e2f141d2af292aca90b53435122a760f362712`. Frozen harness hashes were `74a050576064643415b37c3d69edd14bb6f41550c1fbce9f2577126c0bd244a9` (runner), `dee29232f28f667801c7f134f5184b03339f160d0508ef284b2d873e072ad821` (fixture) and `723af3a3ca8bc9124d31789f58077f78954b0db3cb77c8339104ca8dd9285c46` (MCP service).

Early retained runs exposed an omitted archived-task read, a protected-Git-metadata permission denial, a timeout and one CLI usage-limit response. The skill's existing active/archived reconciliation requirement and the synthetic tool schema were clarified. An invocation-local permission profile now passes a no-model preflight allowing fixture Git writes and denying writes beside the service audit; no unrestricted fallback is used. Timeouts/runtime limits stay unverified, and an explicit usage limit stops new sessions while keeping the expected denominator.

Trace and content review confirmed one existing PR was reused, writeback created one link/comment and read them back, lost creation replies produced only the missing approved item, stale authorization blocked merge, and conflict resolution preserved both features and the other dirty worktree. Raw transcripts and private paths remain unpublished.

These results do not establish real Plane/GitHub authorization or network contracts, native model discovery, every host/session format, adversarial isolation or cross-host stability. Existing scoped real-service evidence remains historical in [earlier validation records](../PUBLISHING.md#verification-scope). Host/credential compatibility is ongoing maintenance.

## Final source and publication

During task source CI, a macOS arm64 job was cancelled before acquiring a hosted runner after 15 minutes. GitHub reported capacity constraints; only the terminal failed job was retried, and all 20 push/PR checks then passed on the unchanged task head. During a later queue-recovery attempt, an orchestration guard failed to stop cancellation and also interrupted a running Windows check. Both interrupted checks were re-run in full; the cancellation was not counted as a pass. Superseded task-owned runs were cancelled separately. No required check was bypassed.

Final source/tag CI and publication readbacks are recorded in the [v0.13.0 GitHub Release](https://github.com/SoaringLabs/plane-devflow/releases/tag/v0.13.0). This document records candidate validation and does not itself establish publication. No npm publication or local plugin update is implied by these checks.
