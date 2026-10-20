# Cursor integration

Select the skill in Agent or use its supported slash/picker entry; natural-language requests can name `plane-setup`, `plane-start` or `plane-deliver`. Skills CLI uses `.agents/skills/` for projects and the shared `~/.agents/skills/` for global installation in the tested Skills CLI version; Cursor also supports its own `~/.cursor/skills/` location. Use Agent mode with file/terminal tools for development operations; a chat without those tools can only discuss the workflow.

Inspect existing MCP servers in Cursor's Tools/MCP settings or `agent mcp list`, and the selected configuration. Global MCP settings live in `~/.cursor/mcp.json`; project settings live in `.cursor/mcp.json`. Merge only the absent Plane entry into the existing `mcpServers` object during explicit setup:

```json
{
  "mcpServers": {
    "plane": {"url": "https://mcp.plane.so/http/mcp"}
  }
}
```

This is a fragment, not permission to replace the whole file. Project configuration writes follow task/file ownership checks. Preserve unrelated servers, settings and existing OAuth. Connect/authenticate Plane through Cursor's MCP UI, or use `agent mcp login plane` with the Agent CLI; the user controls browser consent. CLI/desktop authentication can differ, so verify workspace access on the surface actually used.

Use the shared Git preparation path when managed-worktree tools are absent. Skill installation does not establish model login or Plane access.

Sources: [Skills](https://cursor.com/docs/skills), [MCP](https://cursor.com/docs/mcp).
