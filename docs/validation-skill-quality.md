# Skill authoring and validation changes — pre-release evidence

This record describes the pre-release implementation/testing phase. Publication and the version bump are tracked separately in [v0.8.0 release validation](validation-0.8.0.md); statements below about no publication apply to that phase.

Date: 2026-10-20. Base commit: `3e1245b28e5563e7de03421f1bfd25328267f528`; local branch `codex/skill-quality`. Plugin version remains 0.7.0; no source push, PR, tag or Release was created by this work.

## Changed scope

- Added a development-only PyYAML dependency, package validation and malformed-package regression tests. CI installs development dependencies and validates eval case structure without starting model sessions.
- Added 24 synthetic scenarios, a fresh-session decision runner, explicit rubrics and grader tests. Timeout/missing structured output stays unverified rather than passing.
- Reorganized the three skills by request mode. Detailed PR delivery and finalization procedures moved into conditional references; their original operational checks remain.
- Added README first-use examples, update/remove boundaries and a contributor entrypoint; release rules remain in PUBLISHING.

No runtime helper, MCP endpoint, plugin manifest, marketplace, mapping schema or state-transition implementation changed. The original primary checkout and its pre-existing untracked file were preserved; edits are in the isolated worktree.

## Offline checks

Development environment: Python 3.14.3, PyYAML 6.0.3. Python 3.10/3.14 CI remains configured; remote CI was not run because nothing was pushed.

| Check | Observed result |
| --- | --- |
| Full Python suite | 252 tests passed in 148.210 seconds (227 existing + 25 added) |
| Package failure fixtures | 15 tests passed: malformed/duplicate YAML, missing/invalid fields, name mismatch, nested links/anchors, payload escape/symlinks, UI fields, missing assets/scripts, version/marketplace drift, README source and optimized Python failure status |
| Decision grader and runner errors | 10 tests passed, including unsafe extra decisions, wrong route, missing decisions, alternate handoff labels, malformed rubrics, timeout and absent structured output |
| Package validator | Passed: three skills and 13 reachable plugin Markdown files; repository links also checked |
| Skill Creator quick validation | All three skills passed |
| Extracted payload | Package validation and real helper `--help` startup passed after removing the fixture source checkout |
| Offline demo | Passed; `live_services_called=false`, local start/resume/delivery and synthetic synchronization demonstrated |
| Whitespace/diff | `git diff --check` passed |

Commands and development dependencies are documented in [CONTRIBUTING](../CONTRIBUTING.md). The malformed-package and grader tests verify actual rejection/error behavior; they do not match SKILL wording or heading counts.

## Decision evaluation evidence

[Sanitized run summary](../evals/results/skill-quality-2026-10-20.json). Raw prompts, decisions and JSONL command events are retained outside tracked source in the local task artifact directory. Reproduction and scope are in [evals/README.md](../evals/README.md).

- CLI 0.163.0; default model, no model override. The exact resolved model is not identified in the event output and is not pinned, so this is a smoke comparison rather than a controlled cross-model benchmark.
- Original and candidate each ran all 24 scenarios in fresh read-only sessions, one repetition per scenario. Under the final reviewed rubric, both score 24/24; critical forbidden decisions: zero. This shows no observed decision regression in these scenarios, not improved task success or statistical reliability.
- Finalization received a later pointer to the existing writeback contract. The four affected finalization scenarios were run three times each on that final payload: 12/12 passed, zero critical forbidden decisions. The other 20 candidate scenarios are unaffected by that reference-only change; no claim of a second full 24-case run on the final payload is made.
- Every completed command event in the 60 evaluated sessions was a local `cat`/`sed` document read. Routed cases read the relevant SKILL. No live service or plugin-helper commands were observed. The harness explicitly asks for decisions, so this is not evidence of real business operations executing correctly.

Payload digests:

| Payload | SHA-256 |
| --- | --- |
| Original | `55ed33336702bcbb3ca5b8ca3976d8b14fb2372b60439db0eef3442685efa21c` |
| Candidate suite | `d9ad88005ec25ab83c0e9e3ef171bd88d0973addf1b6385f343965d951aeb43e` |
| Finalization follow-up/final payload | `ade1c813b4cc7458a467cfe3dd28b949cd5e8ad7b578d07edcf7bf25403cdddf` |

### Rubric corrections, with original scores retained

The original baseline score was 23/24; the first candidate score was 22/24. Trace review found three label-level false negatives:

1. START-05: the fixture has ambiguous identity and no independent task content. Asking for the task ID and stopping is valid; an additional `discuss_only` label was redundant.
2. SETUP-01: valid authentication is already supplied by the fixture. Reusing it without an extra `inspect_auth` label is valid; automatic binding/project creation/auth reset remain forbidden.
3. DELIVER-02: `report_handoff` and `handoff_runtime` represented the same intended handoff. The candidate rationale included entry, test steps and resource retention; an explicit alternative group accepts either label while still requiring source/path/preparation/verification decisions.

Original raw results were preserved; separate rescored summaries use the same final rubric for both payloads. No failed model runs were silently dropped and no feature improvement is inferred from regrading. Grader regression tests cover alternate labels and missing handoff. The human criteria remain broader than the machine-scored action projection.

## Retained boundaries and readability

| Contract | Retained source |
| --- | --- |
| Discussion/check-only has no repository/config/state writes | Start route table; Setup check path; checkout first-write contract |
| Explicit task ownership, isolated base-derived worktrees, actual execution path | Start preparation; checkout and parallel-tasks references |
| Existing authorization is reused; task text/receipts cannot grant it | All three entrypoints; task execution and finalization |
| Partial/full acceptance and merge authorization stay distinct | Deliver shared rules and finalization steps |
| Fresh head/base/checks and exact-head merge | PR delivery, finalization, task execution |
| Basic/native/legacy keep their state owners and completion policy | Setup, Start, Deliver and original runtime helpers |
| Partial writeback retries only the failed part; PR reused | PR delivery and workflow |
| Runtime preparation is on demand; user resources preserved | Deliver and acceptance-environment |

Whitespace-separated word counts for entrypoints (not token counts): setup 995→673, start 991→725, deliver 1148→559. Total entry text decreases about 38%; conditional procedures remain available. This measures entry readability/volume, not end-to-end context savings or model quality.

## Unverified scope

Native client discovery, a fresh native plugin install/update/remove, real OAuth/MCP calls, actual Plane/GitHub writeback, remote CI and product/user acceptance were not performed. The extracted payload check proves startup/path independence only. The decision harness uses a supplied discovery catalog and synthetic fixtures; native discovery and real effects require separate client/integration evidence. The primary user plugin installation and live accounts were not changed.
