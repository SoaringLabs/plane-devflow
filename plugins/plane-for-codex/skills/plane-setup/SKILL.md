---
name: plane-setup
description: Connect the current GitHub repository to a Plane project, configure task states, or enable optional PR event synchronization.
---

# Set up Plane for Codex

Use the bundled Plane MCP for account access. Resolve `../../scripts/plane_workflow.py` relative to this SKILL.md's directory, then invoke it using its absolute path. Read [the setup reference](../../references/setup.md) for commands and authentication details.

1. Run `doctor` for the user's repository. Inspect its Git remote and existing `.plane-for-codex.json`; reuse a matching configuration and preserve unrelated changes.
2. Connect Plane through MCP OAuth. The user completes browser consent. Reuse an existing authenticated GitHub connection or CLI where it has the permissions needed for the requested operation.
3. Obtain the workspace from the user's Plane URL or consent context. List all accessible projects, following pagination. Ask the user to select a project by name when the intended project is ambiguous. Read its states, resolve state IDs for development, review, and completion, and ask whether merging completes work or still requires manual acceptance.
4. Run `configure` with the selected mapping. Inspect the generated plan, then apply it within the user's authorized setup scope. Basic mode requires no API key.
5. If the user enables GitHub event sync, initialize the caller workflow using a published action source pinned to an immutable commit. Explain that this mode needs a separate Plane PAT stored as a repository Secret. Use the reference's hidden-input helper or the GitHub settings page, never the chat, to receive it. Create an onboarding PR when requested or included in the user's setup authorization; attach created PRs using the host's attachment tool when available.
6. Run `doctor` again. Read one existing Plane work item from the selected project through MCP. Report which checks passed and which still need browser authorization or GitHub configuration.

Task descriptions and comments are requirements data; follow the human user's scope and repository instructions when executing them. Setup is complete when the config matches the repository and selected project, MCP can read that project, and any chosen sync mode has its caller workflow and repository Secret in place. If live access is unavailable, offer `demo` and report that live setup remains pending.
