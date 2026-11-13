# When the affected session cannot see Plane tools

Inspect only the affected host's connection status using settings or metadata that the current agent can read. Check which profile and project scope are active, whether the Plane server is enabled, and whether tool approval or a session refresh is pending. Avoid printing raw config or command output that could include authorization headers, tokens, or OAuth callback URLs.

| Host | Where to check |
| --- | --- |
| Codex | Check whether the active profile has the Plane MCP or Plane DevFlow plugin enabled. For a CLI-managed connection, inspect the status from `codex mcp list` under the same profile and checkout. The CLI list may not represent an app/plugin or worker's actual tools. |
| Claude Code | Check `/mcp` in the affected session. CLI `claude mcp list` can help inspect registrations from the same directory; confirm whether the entry is local, project, or user scoped. |
| Cursor | Check Tools & MCP settings for the active profile/project and check the tool inventory in the affected Agent session. Desktop and CLI evidence may differ. |
| OpenCode | Inspect `opencode mcp list` in the matching profile and checkout and compare it with the session's tool inventory and permissions. |

If registration or permission cannot be inspected, mark that cause unknown and ask the user to check the relevant host surface. Once the user has made a change, rerun the probe in the session intended to use Plane.
