# Claude Code integration

Pass `--agent claude-code` on task `prepare` calls; preserve its returned execution ID within this chat.

Invoke `/plane-setup`, `/plane-start`, `/plane-deliver`, or request the named skill in natural language. Skills CLI targets `.claude/skills/` in the selected project/user scope; the shared workflow does not require Codex UI metadata.

Inspect `claude mcp list` and `claude mcp get plane`. For an absent connection during explicit setup, select the intended MCP scope independently from skill installation scope. User-scope example:

```sh
claude mcp add --scope user --transport http plane https://mcp.plane.so/http/mcp
```

Project scope uses `--scope project` and `.mcp.json`; it is a repository artifact subject to the existing file-scope preflight. Preserve existing entries and authorization. Run `/mcp` in Claude Code, select Plane and let the user complete browser authentication when needed. Verify read-only workspace retrieval after the connection becomes available. Claude model/account login is separate from Plane OAuth.

Use Claude's normal terminal with the recorded task directory. Its worktree mode is optional; resume the shared helper's task binding before creating another directory. Keep normal permission prompts and action-level authorization.

Sources: [Skills](https://code.claude.com/docs/en/skills), [MCP](https://code.claude.com/docs/en/mcp).
