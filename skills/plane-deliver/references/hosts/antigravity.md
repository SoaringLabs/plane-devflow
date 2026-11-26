# Antigravity integration

Use `/plane-setup`, `/plane-start`, `/plane-deliver` or `/plane-check` in the target repository. Use the shared Git preparation path with `--agent antigravity` and retain the returned execution ID for this session. Resolve Python helper paths from the loaded skill and run Git and Python in the intended repository.

The GitHub-installed plugin declares the Plane MCP server. Reuse a working Plane connection if it already serves the intended workspace. For a new connection, use **Sign in** for the installed plugin in `/plugin` or the app's plugin MCP settings and complete browser OAuth. The bundled server key can appear as `plane-devflow_plane`. Inspect the actual tool names and schemas and run `/plane-check` against the expected workspace before running setup or a task. Keep credentials in Antigravity.

If the skills were installed separately, add the Plane server through Antigravity's MCP settings when explicit setup calls for a connection. Merge `"plane": {"serverUrl": "https://mcp.plane.so/http/mcp"}` into the existing `mcpServers` object. Use `~/.gemini/config/mcp_config.json` for a profile or `.agents/mcp_config.json` for a workspace. Reuse existing servers and keep unrelated entries. Project configuration writes follow the repository's file-scope checks.

Refresh a GitHub-installed plugin through Antigravity using its original GitHub source, then open a fresh session. The standalone and Codex installation helpers manage their own distributions.

See [Antigravity plugin management](https://antigravity.google/docs/plugins) and [Plane MCP setup](https://developers.plane.so/dev-tools/mcp-server#antigravity).
