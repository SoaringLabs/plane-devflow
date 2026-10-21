# First-project onboarding candidate validation

Scope: continuous preparation/install/account guidance, portable setup handoff, first-task drafts and creation reconciliation. The public inventory remains three skills. State synchronization, completion policies, merge/acceptance gates and local finalization are unchanged. This candidate is not a version release or a global installation update.

## Executed checks

- Python 3.14 full suite: **357 passed**, including 24 added regression tests for bootstrap, setup handoff and task-plan recovery. Existing state/finalization tests pass.
- Node.js 24 installer/credential-isolation suite: **23 passed**.
- Canonical/standalone package validation, deterministic generation check, skill frontmatter checks, eval dataset validation (**39 cases**) and diff whitespace checks passed.
- Actual isolated `npm run test:skills` passed: candidate source installation/discovery, repeated installation, self-contained helpers, MCP dependency parsing, removal and preservation of the original profile metadata. It did not perform OAuth or live Plane access.
- Actual isolated `npm run test:integration` passed: packed candidate installation and native discovery of the three qualified plugin skills, with original profile metadata unchanged.
- npm dry-run payload contains both new runtime helpers and excludes tests, virtual environments and private evidence. Existing offline demo passed without live service calls.

## Fresh-session decisions

Codex CLI 0.163.0, CLI default model (no override, model not pinned), one fresh session per case, two concurrent jobs. Host configuration/rules/memory/plugins/hooks were disabled by the repository eval runner; discovery used a supplied synthetic catalog. Sessions could read local documents but executed no business helpers or service writes.

Decision-evaluation plugin payload SHA-256 (before the Python 3.10 syntax correction below):

```text
c832ee7f3ba63a8647165f0b3649e9c9bb099123d18cacb4b327b6360d5ff46d
```

- **9/9 passed**, zero forbidden boundary decisions: ONBOARD-01/02, PLAN-01 through PLAN-05, SETUP-03 and START-01. Command traces show the new first-project/task-planning references were read on their respective routes.
- The common four-case baseline comparison passed **3/4 before, 4/4 after**. The baseline omitted reconciliation/readback decisions for approved task creation. A single sample is not a stability estimate.
- An earlier candidate run scored 8/9 because PLAN-01 redundantly required both `draft_tasks` and `discuss_only`; its rationale already explicitly limited work to chat drafting. The rubric now requires drafting and forbids mutations. Original results were preserved; separate rescoring yielded 9/9, followed by the fresh final-payload 9/9 run above. Baseline was also separately rescored against the current rubric. Initial candidate runs spanned small reference revisions and are not final-payload evidence.
- Raw synthetic prompts, command traces, original results and rescored results remain outside the checkout; only this sanitized summary is published.

## Minimum-Python correction

The initial cross-platform CI caught a Python 3.10 import failure: the new handoff formatter reused double quotes inside a double-quoted f-string, a syntax accepted by the local Python 3.14 interpreter but unsupported by 3.10. The formatter now uses compatible quoting. The original failed run is retained on the PR; recovery and extracted standalone checks were rerun after the fix, with full minimum-version validation reported separately on the PR.

The correction changes quoting only; all workflow documents read by the nine decision sessions remain byte-identical. Final runtime payload SHA-256:

```text
6ac142e2a9f51013fa71c68cc84981379b2d500dc6c1fb29c05a456fe1833953
```

## Limits and manual review

Decision self-reports do not prove live task creation or authorization enforcement. Deterministic tests exercise helper effects separately. Fresh-computer installers, browser OAuth and real MCP task creation/correlation-field readback remain unverified. Cross-platform CI is reported on the PR separately from these local macOS checks. Concurrent creators can race; reconciliation does not assert server-side uniqueness. Background synchronization connection and real PR-event writeback remain separate facts.

Use [the candidate review checklist](review-first-project.md). Load the checkout's payload for review; public commands pointing at main will continue to resolve the published version until this candidate is merged/published.
