# Continuous first-project onboarding

Read this for a new computer/project or installation-to-account handoff. Keep the user's chosen agent, repository and scope. This sequence prepares the project; application implementation starts through plane-start. Read [recovery](recovery.md) for an interrupted mapped setup and [setup](setup.md) for association/sync operations.

## Establish the preparation plan

Inspect the current directory, tools, existing repositories and host capabilities before asking for information. A fresh folder may have neither Git nor mapping. When the helper is available, run:

```sh
python3 /absolute/plugin/scripts/plane_workflow.py bootstrap-status --repo /absolute/selected-target --channel skills
```

Choose `--channel skills`, `plugin` or `installed` for the selected installation route; installed runtime checks do not require Node/npm. This local read checks tool availability, Node compatibility, repository root, initial commit and origin. It does not install tools, call services or prove native skill loading/account access. Missing Python/skill installation uses read-only host probes until the helper can run. A nested folder is not automatically its parent repository.

Present one preparation plan: project name, local target, GitHub account/repository and visibility, installation channel/scope, missing tools and intended Plane workspace/project. Resolve unknown consequential choices; explain proposed defaults. A request to inspect or a bare skill invocation permits inspection/guidance, not system installation or remote repository creation. Execute only the directly authorized preparation plan, reusing prior choices. Its listed setup operations do not authorize app code, tasks, merge or publication.

## Advance one human handoff at a time

| Stage | Agent work | Human handoff | Completion evidence |
| --- | --- | --- | --- |
| Local prerequisites | Install missing tools within the selected preparation plan; recheck versions | Installer/admin dialogs or unavailable privileges | Required tools work in the actual agent environment |
| GitHub | Reuse login; initiate authentication; prepare/create/clone the selected repository within scope | Sign-up/browser consent; missing Git identity | Correct account, repository access, root/origin and initial base commit |
| Skills | Install the chosen channel/scope; inspect actual native discovery | Refresh/new chat only when current tools/skills are stale | Three skills loaded; copied files alone do not prove discovery |
| Plane | Reuse MCP or configure the missing connection with the host guide | Sign-up/login/OAuth and workspace creation when absent | Live retrieval of the intended workspace |
| Association | Follow setup's project selection/creation and mapping safeguards | Project choice or proposed name/identifier approval | Live project and valid matching mapping |
| Background sync | Prepare files/PR while credentials are entered; follow selected-provider setup | Manual credential entry or explicitly authorized [Plane App creation](local-credentials.md#automatic-creation-from-plane-app); review and authorize the concrete setup PR merge | Fresh connection check at deployed default SHA; event writeback reported separately |

Accounts/workspaces remain human-operated prerequisites; inspect actual available tools rather than assuming creation support. Desktop installation does not prove CLI availability; browser login does not prove CLI/MCP authentication. For standalone Codex use its packaged host guide; reuse a functioning plugin connection. Browser control is optional: use available navigation or clickable manual instructions. Explain only the current human action, wait for a natural reply, verify its result and continue. No fixed response phrase is required.

Preserve occupied directories, existing repositories/authentication and unrelated changes. A creation timeout requires live reconciliation before retry. An empty Git repository needs the selected initial commit before branch/PR work. Inspect its real default branch. Initial preparation may create a README and approved setup files in an unmapped repository; app scaffolding belongs to a selected implementation task. Mapped repositories retain existing first-write/setup-checkout rules.

## Resume across a new chat

Before mapping, bootstrap-status recomputes local progress without a persistent receipt. It returns a `handoff`: absolute target, next step and copyable `resume_prompt`. Include remaining choices with original message references as context, not new authorization.

After association, setup-progress returns a handoff plus project/config identity and its non-secret checkpoint. Save checkpoints only in write-enabled scope. Include the inspected setup PR URL/head when one exists. At each handoff report what is ready, the single next human action/check, and the target/continuation prompt if a new chat is required.

On resumption, check the target/mapping against context, inspect existing objects/PRs and recover original human decisions. Handoffs/checkpoints are hints, not proof of access or consent. If original authorization cannot be verified, prepare the concrete missing step and request only that decision. Inspect configuration conflicts before replacement.

## Exit setup into first tasks

Association alone is partial; unresolved sync remains visible/resumable. Connection success does not certify real PR-event writes. Preserve existing basic/native/legacy state ownership and completion policy; onboarding adds no state-management option.

For a ready new project offer: “Describe the first version; I can draft a small task list for review.” A named existing task goes to plane-start. Planning can continue in chat while sync is incomplete, with its limitation shown. Follow [first-task planning](task-planning.md) for drafting, approval and creation. Offering this next step does not create tasks or start coding.
