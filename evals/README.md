# Skill behavior evaluations

`cases.jsonl` contains synthetic scenarios covering the three entrypoints: explicit requests, implicit routing, unrelated requests, read-only scope, credential reuse, recovery, task/workspace identity, partial acceptance, stale evidence and partial writeback. `actions.json` defines decision labels for scoring; labels are not executable commands.

## What each check proves

- `python3 evals/run.py --validate-only` validates case IDs and rubrics. It does not run a model.
- The opt-in runner starts a fresh `codex exec` read-only session per case. It supplies only the scenario, skill name/description/path catalog and action vocabulary, then captures local document reads and a structured decision. Expected answers and rubrics are withheld from the evaluated session.
- Scoring compares the selected entrypoint, required decisions and forbidden decisions. Missing results are unverified and cause failure; forbidden decisions in a critical-boundary case are reported separately.
- This is a **decision-only eval with emulated discovery**, not a native skill-install/discovery test, real Git/Plane/MCP execution or end-to-end acceptance. A model saying it would preserve data is not proof that a tool actually did. Use the deterministic tests for helper behavior and separately authorized client/service checks for external effects.

## Reproduce

Install development dependencies as described in [CONTRIBUTING.md](../CONTRIBUTING.md). The model run additionally requires an authenticated Codex CLI supporting the flags shown in `run.py` (first checked with CLI 0.163.0). It consumes normal model usage; CI only validates the dataset.

```sh
.venv/bin/python evals/run.py --validate-only
.venv/bin/python evals/run.py --plugin /absolute/baseline/plugin \
  --output /tmp/plane-evals-baseline --label baseline --jobs 2
.venv/bin/python evals/run.py --plugin /absolute/candidate/plugin \
  --output /tmp/plane-evals-candidate --label candidate --jobs 2
```

Use new output directories; the runner refuses to overwrite an existing run. `--case START-01` selects a case, `--repeat 3` repeats fresh sessions, and `--timeout 180` bounds each session. Up to four jobs are supported. The model uses the CLI default without a model override; record any environment/default-model differences before comparing runs. A single repetition is a smoke baseline, not a stability estimate.

User config, rules, plugins, memory and hooks are disabled for the evaluated invocation, with host skill discovery skipped in favor of the supplied catalog. `skip_host_skill_discovery` is a development feature; inspect the captured warning and CLI compatibility. These flags are not a general network/security sandbox: use only synthetic fixtures, read-only sandboxing and a trusted local runtime. Do not put real credentials or account data in fixtures or enable production tools to make a test pass.

Each run records the payload digest, exact prompt/command, CLI version, decision, command events, errors, timing and scoring. Raw output goes outside the checkout or into ignored `.plane-devflow.local/`; the runner will not publish it. Review command events to confirm relevant documents were actually read and check for unintended actions, rather than trusting only the final JSON.

## Maintain the rubric

`must_observe` and `forbidden_effects` are human-review criteria. `required_decisions`, optional `required_decisions_any` alternative groups, and `forbidden_decisions` are the narrower machine-scored projection. Do not infer that a required label proves the entire human criterion. Add discriminating actions/scenarios for demonstrated failures, not exact prose matches.

If a score conflicts with the trace, inspect the fixture and rubric first. For example, an ambiguous task with no useful independent information can correctly stop after asking for its ID; it should not fail merely for omitting a redundant “discussion” label. Preserve original scores and explain regrading rather than hiding failed runs. Use `--rescore /tmp/plane-evals-baseline` to write a separate `rescored.json` against the current rubric without invoking a model or overwriting original results.

Publish only a sanitized summary with source/rubric digests, counts, repetitions, observed failures and limits. Keep original and candidate conditions comparable. Package checks, decision tests, native discovery and real event writeback remain separate evidence.

## Execute synthetic workflows

`execution.py` is a separate, opt-in execution assessment. The model reads a skill and actually uses Git/Python helpers and a synthetic Plane stdio MCP service. A disposable bare Git origin and GitHub CLI adapter replace external services. Each case has separate repositories, worktrees and service state; no real Plane/GitHub connection is configured.

```sh
.venv/bin/python evals/execution.py --validate-only
.venv/bin/python evals/execution.py --output /tmp/plane-execution-candidate --repeat 2
# Retry a specific terminal failed/unverified case in a new evidence directory:
.venv/bin/python evals/execution.py --case EXEC-WRITEBACK --output /tmp/plane-execution-writeback
```

Run offline grader/fixture regressions with `python3 -m unittest discover -s tests -p 'test_execution_evals.py' -v`. They deliberately inject wrong task edits, duplicate creates, missing writeback/readback, stale gates and dropped conflict behavior. They are not model scores. Model execution uses the authenticated Codex CLI's default model and consumes normal usage; default tests/CI never invoke it.

The five cases cover wrong-directory task recovery, PR-success/Plane-writeback recovery, lost creation replies, stale merge evidence and a real conflicting base merge. The grader checks protected files, Git branches/remote refs, actual helper output, service effects/readback and completed tool events. Final model prose cannot satisfy these checks. Inspect traces and report/comment content too: these mechanical assertions do not establish complete semantic quality or adversarial tamper resistance.

Payload, cases, action catalog and harness source snapshots are frozen before sessions. Decision and execution runners write a start manifest; the original and rescored verdicts remain separate. Execution stdout/stderr stream to the private evidence directory. Runtime errors/timeouts stay unverified; a usage-limit response stops new sessions and explicitly marks remaining cases unrun, without dropping them from the denominator. Re-run only terminal affected cases in a new directory after checking runtime availability. Never silently overwrite a failed run.

Only the synthetic MCP tools are pre-approved by invocation-local configuration. Shell commands use an invocation-local permission profile that permits only the fixture workspace and its synthetic Git metadata to be written; a no-model preflight verifies Git writes and denies writes beside the service audit. No unrestricted fallback is used. inherited tool credentials are excluded, and the shared service audit is outside the evaluated workspace. This is not a general security sandbox: use synthetic inputs, a trusted local runtime and no production tools. Do not copy user authentication into fixtures. Existing model login is distinct from Plane/GitHub authorization. Native skill discovery, real OAuth, real service contracts and cross-host stability require separate evidence.

The service implements the minimal [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) and [tool messages](https://modelcontextprotocol.io/specification/2025-06-18/server/tools). Invocation-local fixture approvals use the documented [per-tool MCP configuration](https://learn.chatgpt.com/docs/config-file/config-reference).

### START-10 rubric correction

Two retained task-1 decision runs scored 3/4 with no forbidden actions. In START-10 the rationale explicitly kept a supplied sync limitation separate from discussion, while action labels omitted `report_partial` and `review_sync_bundle`. Discussion does not require inspecting a bundle. The machine projection now requires discussion-only routing; human trace review still requires the supplied limitation to be reported and all original forbidden effects remain. Original scores are preserved; a rescored result or new session must be identified separately. This correction does not turn decision tests into execution proof.

### Equivalent routing and handoff projections

A retained release-candidate run scored 42/45, with zero forbidden actions. Review found three narrower machine projections: SETUP-02 required manual Secret guidance even when the next safe step was local credential inspection; ONBOARD-02 required one of two equivalent handoff labels; UPDATE-01 required no skill even when setup's manual-update reference was read without business setup. The rubric now accepts only these explicit alternatives. All human criteria and forbidden effects remain. `expected_skills_any` lists reviewed equivalent entrypoints; unrelated requests still require no Plane skill. Original strict scores, separate rescores and fresh runs must be reported separately; input snapshots are never rewritten.
