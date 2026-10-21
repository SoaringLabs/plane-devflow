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
