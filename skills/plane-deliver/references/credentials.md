# Guided Actions credentials

Read this when the user selected Actions and the mapped repository lacks a usable runner Secret. Existing OAuth is for the current agent; the PAT is for GitHub Actions. Native mode skips this entire flow. A missing/unknown connection check does not by itself mean the PAT is missing: inspect Secret metadata first and reuse existing configuration. Do not overwrite an existing Secret without the user's replacement intent.

For the manual browser branch, the expected interaction is staged: guide the current page, explain the one human step, wait for that step's confirmation, then open the next page. Continue authorized independent preparation while waiting. A bare final message linking GitHub Secrets is not completed credential guidance. Use an asynchronous question, when available, to keep the handoff pending; request only progress confirmation, never token text. If the turn must end for human input, state the exact current step and how to resume. Any natural confirmation of completion is sufficient. Use [recovery.md](recovery.md) for capability routing, checkpoint commands and failure handling; save only the human-reported enum after each confirmation.

## 0. Check reuse before creating a token

Check the current repository Secret first. If it exists, continue connection verification. If missing, use `credential-guide --step local`; follow [local credentials](local-credentials.md) to select the Plane account, inspect local storage and offer opt-in reuse on macOS or Windows. This path works across GitHub owners and organizations. No organization-level Secret is required. If local storage is missing/unavailable, offer human input of an existing PAT; generate a new token only when needed. The manual store/transfer helpers operate in a human-controlled terminal, without returning the PAT to the agent.

## 1. Choose the explicitly authorized creation route

When the user explicitly requests creating a PAT and saving it on this Mac,
follow [automatic creation from Plane App](local-credentials.md#automatic-creation-from-plane-app).
Valid session authentication lets the helper create and store the PAT in-process;
missing/expired authentication prompts login and resumes the same operation.
Choosing Actions alone does not enable this branch. Keep manual entry available.
After automatic local saving, use the local saved-credential branch, not a prompt
claiming the user copied the PAT. GitHub upload remains separately human-operated.

### Manual Plane token creation

Run `python3 /absolute/plugin/scripts/plane_workflow.py credential-guide --repo /absolute/repo --step plane`. This validates the current origin/mapping and returns the correct Plane origin/workspace, suggested title/description, and navigation. It performs no account writes.

Prefer an already authenticated Plane app or browser when the host exposes it. Otherwise open the returned URL using an available browser-opening tool. Browser control is optional and host-specific: discover capabilities rather than importing another plugin's private modules or declaring an unavailable mandatory dependency. If no opener exists, provide the actual clickable URL and the full settings path.

Navigate **avatar / Open user menu → Settings (Profile settings) → Personal Access Tokens → Add access token**. UI labels may say Add personal access token. Use current observed UI, not invented selectors or an unverified `/profile/api-tokens` URL. As verified in Plane Cloud on 2026-10-10, this opens a settings modal; the task URL does not change. Do not promise a stable direct PAT page URL.

Show the suggested title (`Plane DevFlow: OWNER/REPO`) and description. Explain the expiry field; the user chooses an explicit expiry appropriate to the automation and will need to renew it before expiry. Confirm they are using the intended Plane account/project permissions. No paid upgrade or new Plane project is required solely for this credential step.

With computer/browser use, navigate to the form and optionally fill non-secret title/description. Stop before **Generate token** and hand control to the user to generate and copy it. Do not capture the page/AX tree after generation while the token is visible, read clipboard contents, inspect DOM token values, or move the credential through agent memory/files/tools. Login, CAPTCHA and credential creation follow the host's handoff/confirmation rules. If the user already has a suitable PAT, skip creation after their confirmation. Offer the optional [remember-on-this-computer route](local-credentials.md#human-operated-entry-and-reuse); it is not enabled by default.

Ask only whether the token is ready, e.g. “在 Plane 页面生成并复制 token，完成后告诉我‘已准备好’；不要把 token 发到聊天里。” Do not open GitHub prematurely or couple this question to merge approval.

## 2. Open the mapped GitHub repository's Secret form

After the user confirms a PAT is ready, run `credential-guide --repo /absolute/repo --step github`. Open the returned **current repository** URL, not a test repository or account token page. The destination is **Settings → Secrets and variables → Actions → New repository secret**.

If host control is available, navigate to the form and fill only **Name = PLANE_API_KEY**. Do not read any existing Secret value or observe a new Secret field after the user starts pasting. Hand off to the user to paste the PAT into **Secret** and click **Add secret**. Credentials go directly from the user to GitHub; there is no agent-mediated clipboard bridge. Ask for “已保存” or an equivalent natural confirmation. If there is a permission/SSO blocker, identify it and keep the successful project association; do not create another token as a workaround.

Without browser control, still open the form via an available browser-opening tool or give the exact clickable link and field instructions. Offer the hidden-input `set-secret` terminal route only if the user prefers it. Do not launch a hidden terminal awaiting credentials without a human-visible prompt. Do not request a token via chat, a text questionnaire, a shell argument, or an environment dump.

## 3. Verify storage, then continue activation

Once the user says it is saved, run `credential-guide --repo /absolute/repo --step verify`. It lists **only Secret names and update times**, checks `PLANE_API_KEY`, and never reads the value. If absent, verify the repository/name/scope with the user rather than claiming success from a screenshot or confirmation alone. API/permission failures are unknown, not proof of absence. No need to read the Secret form or the user's clipboard for verification.

Presence proves storage, not PAT validity, project access or event delivery. Continue `check-github`; keep the setup PR linked to its actual head and obtain any still-missing merge authorization separately, respecting already supplied authorization. After trusted files reach the default branch, perform the read-only connection dispatch and report actual PR writeback separately. Do not require a fixed phrase like “合并并验证” to resume; a user can finish the credential stage without authorizing merge.

## Sources and limits

- [Plane API key creation](https://developers.plane.so/api-reference/introduction).
- [GitHub repository Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).
- [OpenAI plugin architecture](https://developers.openai.com/plugins/concepts/plugins) and [Skill/tool orchestration](https://developers.openai.com/plugins/build/skills): a Skill can describe this workflow; live UI tools must be available in the host. A plugin installation alone does not guarantee browser-control capability.

No new PAT was generated or transmitted during the 0.4.1 implementation's UI verification. Only the existing Plane account's settings and unsubmitted creation form were inspected.
