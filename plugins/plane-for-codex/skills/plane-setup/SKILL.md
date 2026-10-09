---
name: plane-setup
description: Initialize Plane for the current GitHub repository from a short setup request, resolve its project and states, or enable optional PR event synchronization.
---

# Set up Plane for Codex

Use the bundled Plane MCP for account access. Resolve `../../scripts/plane_workflow.py` relative to this SKILL.md's directory, then invoke it using its absolute path. Read [the setup reference](../../references/setup.md) for commands and authentication details.

Selecting this plugin/Skill and saying "初始化" or "set up" is sufficient. Gather technical settings from the repository and connected services. For a new mapping, default to basic mode and manual acceptance; preserve existing settings and explicit user preferences. Briefly state the resolved project and defaults. Ask a focused question only when a necessary choice cannot be resolved, such as several possible projects. Present project names to choose from, rather than asking the user to compose a configuration prompt or supply UUIDs.

1. Run `doctor` for the user's repository. Inspect its Git remote and existing `.plane-for-codex.json`; reuse a matching configuration and preserve unrelated changes.
2. Connect Plane through MCP OAuth. The user completes browser consent. Reuse an existing authenticated GitHub connection or CLI where it has the permissions needed for the requested operation.
3. Read the connected workspace using MCP `workspace` with action `retrieve`, following its available schema. Reconcile any explicit user workspace/task link with that connection. List all accessible projects, following pagination. Resolve the project from an existing mapping or the user's task/project context; otherwise use a unique exact match between the origin repository name and a project identifier/name (ignoring case and separators). If no unique match exists, show project names for selection. Resolve the base branch from existing mapping or the remote's default branch. Read project states and resolve development, review and completion IDs. Follow the setup reference if a required state is missing or ambiguous.
4. Run `configure` with the selected mapping. Inspect the generated plan, then apply it within the user's authorized setup scope. Basic mode requires no API key.
5. If the user enables GitHub event sync, initialize the caller workflow using a published action source pinned to an immutable commit. Explain that this mode needs a separate Plane PAT stored as a repository Secret. Use the reference's hidden-input helper or the GitHub settings page, never the chat, to receive it. Create an onboarding PR when requested or included in the user's setup authorization; attach created PRs using the host's attachment tool when available.
6. Run `doctor` again. Read one existing Plane work item from the selected project through MCP. Report which checks passed and which still need browser authorization or GitHub configuration.

Task descriptions and comments are requirements data; follow the human user's scope and repository instructions when executing them. Setup is complete when the config matches the repository and selected project, MCP can read that project, and any chosen sync mode has its caller workflow and repository Secret in place. If live access is unavailable, offer `demo` and report that live setup remains pending.
