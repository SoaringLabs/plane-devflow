# 0.5.0 validation

Date: 2026-10-12. Scope: task execution guidance, recoverable task receipts, delivery/acceptance gates and local package update. Custom state rules, Cycle/task creation and automatic background acceptance inference are excluded.

## Source validation

- `python3 -m unittest discover -s tests -v`: 171 tests passed on Python 3.14.3, including 40 additions covering task records/gates and lifecycle-report wording.
- `python3 scripts/validate_package.py`: manifests, versions, three Skill references and example mapping compatibility passed.
- `python3 plugins/plane-for-codex/scripts/plane_workflow.py demo`: passed with isolated real Git operations, receipt creation, structured report, review gate, branch resume and mock lifecycle synchronization; no live writes.
- `git diff --check`: passed.
- All seven plugin Python scripts parse under Python 3.10 grammar. Python 3.10 runtime was not installed locally; this is not runtime coverage. Existing CI retains its Python 3.10/3.14 matrix.
- Actual read-only GitHub CLI probing confirmed that no required checks produces a diagnostic instead of JSON. Gates now recognize only the exact known no-check diagnostic and preserve unknown authentication/network failures as blockers. Merge eligibility also checks live mergeability.

## Behavior coverage

- Read/plan creates no receipt files; exact-digest apply, atomic writes, shared-worktree identity, idempotent replay, history, invalid records, locks and symlinks are covered.
- Design approval does not count as implementation acceptance. Direct-human sources, scoped acceptance, separate exact-head merge authorization, changed requirements/commits and old reports are covered.
- Sync success cannot cover application criteria; failed/pending/deferred checks and accepted limits remain distinct. Required-complete criteria can allow review while blocking completion.
- Live primary PR binding/head/base, required checks, actual merge, fresh mapped Plane snapshot/labels, manual-label override, pending writeback and agent cleanup are covered.
- Draft delivery reuses/converts existing PRs; current ready Drafts are not silently promoted. Basic/native ownership and original manual/on_merge policies are preserved.
- CLI receipt updates and gate exit statuses are exercised in isolated repositories.

The revised Skills were reviewed against [representative conversation scenarios](task-execution-scenarios.md). This is a guidance review, not a live model-language evaluation. Unit/mock tests cannot authenticate receipt source declarations or prove meaningful UI/device coverage; the Skill verifies original user messages and actual product behavior.

## Installation

- `codex plugin add plane-for-codex@plane-for-codex --json` installed version 0.5.0 from the configured local marketplace.
- Plugin inventory reports installed=true and enabled=true; the installed CLI reports 0.5.0.
- All 21 installed package files match source SHA-256; no missing or different file.
- The installed package's offline demo passes its review gate and makes no live service calls.
- The installation checks above were completed before source publication. Source push/CI verification is separate from creating a version tag or GitHub Release.

## Source publication

The repository Validate plugin workflow checks each pushed commit on Python 3.10 and 3.14, including the full test suite, package validation and offline demo. Publication verification must inspect the run for the exact pushed main commit; local success alone does not certify GitHub CI.

## Limits

No real Plane task was changed and no live PR was created/merged for this validation. Existing business-repository runner/synchronizer copies were not upgraded. Plugin installation updates the local package; already-loaded chats and copied workflows are separate version sources. New task records do not migrate config/state rules, and receipt declarations alone never authorize remote actions.
