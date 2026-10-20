# Codex integration

Invoke through the skill picker or `$plane-setup`, `$plane-start`, `$plane-deliver`. The optional `agents/openai.yaml` provides cards and the Plane dependency. Reuse a working native/plugin connection before adding another server.

Inspect `codex mcp list --json` and `codex mcp get plane --json`. When explicit setup needs an absent connection:

```sh
codex mcp add plane --url https://mcp.plane.so/http/mcp
```

Adding the server may immediately start browser OAuth. The user completes consent. For an existing connection still missing login, use `codex mcp login plane`. Preserve a conflicting existing URL and resolve intended source before changing it. Reopen the chat if its tool catalog is stale, then verify read-only workspace access. Existing plugin authorization is not assumed portable to a new server identity.

Managed worktree/artifact tools are optional. Inspect/reuse task attachments when available; otherwise use the shared Git helper. Keep the returned execution directory explicit.

Sources: [Skills](https://learn.chatgpt.com/docs/build-skills), [MCP](https://developers.openai.com/codex/mcp).
