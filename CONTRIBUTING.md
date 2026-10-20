# Contributing

Keep changes scoped to the problem and preserve existing features, authorization boundaries and native/basic/legacy state ownership. A skill wording change can change behavior; review it accordingly. Small fixes need a short explanation, while changes to default behavior or compatibility need an explicit scope and acceptance criteria.

## Where changes belong

- `plugins/plane-for-codex/skills/`: the three public agent entrypoints and their Codex UI metadata. Keep purpose, routing and essential boundaries in SKILL.md; link conditional procedures when the requested mode needs them.
- `plugins/plane-for-codex/references/`: canonical workflows, contracts and recovery. Keep each detailed rule in one place rather than copying it into every entrypoint.
- `plugins/plane-for-codex/scripts/`: standard-library runtime helpers. Preserve read/plan versus apply behavior, structured output, idempotency and protection of unrelated work.
- `bin/` and `lib/`: the npm installer and its persistent-source/native verification boundary. Keep it separate from account authorization and business-repository mutation.
- `tests/`: deterministic behavior and malformed-package regression tests.
- `evals/`: prompts, fixtures, decision rubrics and the opt-in model evaluation runner. Raw transcripts stay outside tracked files.
- `README.md` / `README.zh-CN.md`: matching English and Chinese public entrypoints, installation and first successful use. Contributor/release detail belongs here or in PUBLISHING.

Do not add skill directories or metadata only to match a template. The public inventory is deliberately three skills; an intentional inventory change must update the package contract and its tests. The complete plugin shares scripts/references; standalone installation of individual skill folders is not claimed.

## Local checks

Use Node.js 20+, Python 3.10+ and a development virtual environment:

```sh
npm ci
npm test
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_package.py
.venv/bin/python evals/run.py --validate-only
.venv/bin/python plugins/plane-for-codex/scripts/plane_workflow.py demo
git diff --check
```

PyYAML is a development-only dependency for real YAML parsing. Shipped plugin helpers still use only the standard library. CI runs offline checks on Python 3.10 and 3.14 and installer checks on Node.js 20/24 across macOS, Linux and Windows. `npm run test:integration` packs the real npm tarball and calls the installed Codex CLI from fresh temporary state; it requires Codex but no login or model session. Model evals are opt-in and do not run automatically on forks/CI credentials.

Package validation checks frontmatter types/limits, UI fields, explicit public inventory, versions/resources, reachable inline Markdown/HTML links, images and anchors, and repository installation identity. It rejects symlinks and plugin references escaping the payload. It is not a complete Markdown parser, remote URL checker, security scanner or agent-behavior proof. Extracted-payload tests exercise helper import/CLI startup without the source checkout.

## Skill changes and evaluation

Use [the eval guide](evals/README.md) for fresh-session routing and authorization decision checks. Add a discriminating scenario for a demonstrated failure; avoid tests that merely match wording or headings. Compare the original and changed skill payloads with identical fixtures/settings, keep unexpected failures visible, and inspect actual command events alongside the structured decision.

Decision tests use synthetic fixtures and an explicit catalog; they do not certify native skill discovery, real MCP calls, account permissions or external writes. Those require separately scoped integration/client evidence. Preserve explicit-only or implicit-invocation preferences; do not change invocation policy as a substitute for action-level authorization.

A PR should explain the concrete problem, resulting behavior, affected contracts, actual checks and remaining limits. Include a relevant before/after scenario; do not turn an unexecuted plan into a passed test. Review the exact diff and retain source/license notices for borrowed material. Never include tokens, private task contents, real response snapshots or personal filesystem paths in public artifacts.

For versioning, publication scope and release verification, follow [PUBLISHING.md](PUBLISHING.md). Passing local checks does not authorize push, merge, tagging or release.
