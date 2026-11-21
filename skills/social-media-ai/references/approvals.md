# Approval requests during setup and operation

Ask for a concrete decision after preparing the work it controls. Explain what will happen, which account/data it affects, and any actual cost or external access. Keep the wording short and offer an alternative. Existing authorization is reusable: never make the user approve the same connection, expense allowance, or posting scope again without a relevant change.

## What the agent can prepare itself

A request to set up this workflow covers reading its repository, installing its local skill, checking available tools, creating a separate local workspace, saving nonsecret settings, inspecting the chosen source folder, preparing drafts with already authorized tools, and testing local helpers. Do these steps without a permission question for every command. Never overwrite originals. The user's initial folder choice should make clear that its selected contents are candidates for this posting workflow.

## Questions at actual boundaries

Use only the question relevant now; don't present a checklist of permission requests.

| Situation | Example request after substituting real details |
| --- | --- |
| First social connection | “Shall I connect Instagram through [provider]? You'll sign in on its page and review access there. I will verify the selected account before preparing posts for it.” |
| More than one visible account | “Which Instagram account should I use: @shop or @personal?” Enable only the selected stable ID. |
| Next connection | “Instagram @shop is connected. Would you like to connect another account or continue with the schedule?” |
| Missing system dependency | “Video cleanup needs FFmpeg. May I install it using [actual package manager and command]? It will add the video tools to this computer. We can also continue with photos only.” |
| New paid tool or usage | “This option costs [verified amount/usage terms] through [provider]. Do you want to use it, or keep the workflow within your existing tools?” Don't invent pricing or assume agreement with an unspecified cost. |
| Media sent to an editing service | “May I send these selected files to [editor] for the shown cleanup?” Skip a repeat request when the user has already chosen this editor and allowed that media-processing scope. |
| Public media hosting | “[Publisher] needs a retrievable file URL. May I upload these prepared assets to [chosen host] for delivery? The files will be accessible through those URLs. I will upload only these assets.” A blanket “set it up” does not select an unspecified public host. |
| First preview approval | “Here are [number] prepared posts for [accounts] at [dates/timezone]. Shall I schedule these exact posts, revise them, or leave them as drafts?” |
| Future posting mode | “Should I ask you to approve each new post, or automatically post future media from [folder] to [accounts] under these editing, caption, and timing rules?” |
| Recurrence activation | “Shall I activate [human-readable recurrence] in [timezone] for [accounts], with [review/automatic] mode and a limit of [count]? The next runs are [dates].” If the previous explicit approval already covered this exact activation, execute it without asking again. |

## Save the decision, then act within it

Record approval time, the user's explicit decision, and concrete scope in the private workspace. For ongoing automatic mode, `authorization.scope` should identify the source folder, account IDs, allowed edits and caption rules, posting schedule, and limits. Keep account permissions and any allowed service costs/data-sharing scope separately clear. Store a short append-only history in `approvals.jsonl` if needed; never include passwords, tokens, or authentication callback URLs.

Use the queue's approval record for exact post bytes/caption/metadata/time. In review mode, approving a batch does not approve future batches. In automatic mode, don't ask on every scheduled run; pause and ask only if new work falls outside scope. Adding a new account does not automatically add it to the automatic-posting scope.

If the user declines, record the choice and continue what remains possible. If a scheduled run cannot request approval interactively, keep the affected item as a draft and report the needed decision. Never treat silence, elapsed time, a stored “connected” flag, or a draft preview as approval. Preserve host permission controls; do not change global sandbox or approval settings to make unattended posting work.
