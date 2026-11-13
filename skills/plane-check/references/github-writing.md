# English commit and PR messages

Read before creating development commits, creating/updating a PR, or merging it. Use English prose for the complete subject/title and body of development commits, PRs and final squash/merge commits, regardless of the conversation or Plane task language. An empty optional commit body is fine. Keep Plane task titles/descriptions, Plane progress reports and everyday conversation in the user's language; this policy does not authorize translating the Plane task.

Summarize the actual change in natural English rather than copying a non-English task title. Preserve task IDs, names, paths, commands, URLs and machine-readable metadata. Exact non-English UI strings or source literals may remain when necessary evidence, with English explanation; they are not a substitute for English prose. Language changes must preserve verification facts, limitations and acceptance scope.

## Development commits

Before each commit, review its full subject and body in English, following the repository's existing message format. Include conflict-resolution and base-integration commits created during the task. Before pushing, inspect the new task commits' complete messages, not just their subjects. Apply this policy to new messages; rewriting existing published commits or historical/base commits is a separate scope. Report an existing mismatch that cannot be corrected within the authorized scope.

## PR title and body

Pass an English change summary to `deliver --title`; the helper adds `[PROJECT-123]` but does not translate or validate language. For example, a capsule-control/accessibility change can use `[PROJECT-123] Unify native capsule controls and parameter accessibility`.

Review the entire rendered PR body, including headings, verification evidence, remaining acceptance criteria and environment notes. `render-report --from-progress` copies prose from task receipts, which may be non-English. Translate that prose in the GitHub report copy after rendering while preserving its facts, task/criterion IDs, links and hidden binding/evidence markers exactly. Keep the original receipt in its existing language; translating prose does not change the observed head, receipt digest or acceptance authority. Re-render and retranslate if the underlying evidence changes.

Use separate GitHub and Plane report copies when their languages differ, with the same current head, criteria, verification facts and limitations. Before any create/update (including Drafts), inspect the outgoing title and body. Read back the PR after writing to verify both language and content; correct only the failed part of a partial handoff.

## Final squash or merge commit

Before an authorized merge, prepare and review the complete English commit subject and body from the accepted change and verified results. Explicitly provide both when creating a squash or merge commit; repository defaults can reuse a non-English PR title, description or commit list. A corrected PR title alone is insufficient. Preserve the selected repository-supported merge method and the existing exact-head merge gate and authorization requirements.

With GitHub CLI, use `--subject` and `--body-file` alongside the chosen merge method and `--match-head-commit`; keep the body file outside the checkout. Pass an intentionally empty body explicitly when appropriate rather than falling back to an inherited body. With an API/MCP tool, use its equivalent explicit commit title/message fields. If it cannot supply both, use a supported exact-head operation before merging. See the [GitHub CLI merge reference](https://cli.github.com/manual/gh_pr_merge).

Rebase merging reuses development commit messages; inspect all messages that will enter the base branch instead of assuming a new merge message will replace them.

After merging, read back the actual resulting commit subject and full body from GitHub and verify the English prose and accepted content before claiming the handoff is complete. If a mismatch has already reached the base branch, report it; rewriting merged history requires separate authorization.
