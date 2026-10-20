# OpenCode integration

Ask OpenCode to load the named `plane-setup`, `plane-start` or `plane-deliver` skill through its native skill tool. Do not assume Codex's `$` syntax creates an OpenCode command. Skills CLI uses `.agents/skills/` for projects and `~/.agents/skills/` globally in the tested Skills CLI 1.7.4. OpenCode also supports its native `~/.config/opencode/skills/` location. Keep native tool permission rules; OpenAI UI metadata is optional.

Inspect `opencode mcp list` and the active OpenCode configuration. Use the intended project `opencode.json` or global `~/.config/opencode/opencode.json`, merging only the missing server during explicit setup:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "plane": {"type": "remote", "url": "https://mcp.plane.so/http/mcp", "enabled": true}
  }
}
```

The fragment is not a replacement for the existing file. Preserve other providers, permissions, servers and conflicting entries; project writes follow the shared scope checks. For missing authorization use `opencode mcp auth plane`; the user completes browser consent. Inspect `opencode mcp auth list`, then retrieve the workspace through the actual tools. Model-provider credentials are separate from MCP OAuth.

Use OpenCode's shell tool with the recorded task directory and the standard Git worktree helper. No Codex installation is required for this route.

Sources: [Skills](https://opencode.ai/docs/skills/), [MCP](https://opencode.ai/docs/mcp-servers/).
