# Recurring execution

Choose a scheduler the user's agent can actually operate. Read its current tool schema and capabilities before configuring it. The local helper does not run in the background; a saved due date alone never starts a job.

## Two supported patterns

**Provider scheduling:** Have an authorized social scheduler deliver posts at their approved times. The recurring agent scans and prepares media ahead of time, then submits each approved post once and saves its receipt. Use an exact future slot with the bundled ledger; if a provider can only assign its own queue slot, adapt the timing approval and ledger before using that mode. Recheck remote status on later runs. If the provider accepts local uploads, no separate media host is needed; otherwise use the user-selected host and keep files retrievable for the provider's required duration. Don't submit the same job through both a provider queue and a separate due-time publisher.

**Agent scheduled task:** Use the host's recurring-task capability to run this skill against the selected source folder, profile, and shared queue. Configure only after the first batch is concrete and the posting scope is authorized. Read back the saved task ID, recurrence, timezone, and next runs. If the host has no scheduler, help configure a supported runner or give an exact prepared prompt and clearly label scheduling as inactive until it is installed.

For local-folder work in the ChatGPT desktop app, the project must remain accessible and the machine/app must be running. Web scheduled tasks need accessible connected/uploaded sources; they do not retain access to a folder on the user's computer. Use a persistent workspace and explicit absolute paths rather than a new ephemeral checkout for each run. [Official scheduled-task documentation](https://learn.chatgpt.com/docs/automations).

## Time and limits

Save an IANA timezone such as `Europe/Berlin`, local weekdays/times, and timezone-aware UTC instants for each concrete job. Display the next three local times with offsets before activation. A recurring 09:00 local schedule should remain 09:00 through daylight-saving changes. For a nonexistent or duplicated local time, choose and record a skip/first/second-occurrence policy with the user.

Set a per-account daily cap and a maximum new-job count per run. Before assigning a slot, count existing planned/scheduled/published jobs for that account and inspect the provider queue for jobs created outside this agent. The helper does not enforce these profile limits; the agent must. Use the provider's channel schedule when it supports the desired spacing. For direct publication, only claim due jobs and process at most the authorized batch. Default missed-run handling is to skip elapsed slots and propose future ones, not publish every missed post immediately.

## Durable task prompt

Fill in actual paths and limits before registering this prompt; never include credentials:

> Use $social-media-ai. Read the saved private profile at [absolute profile path] and shared queue at [absolute database path]. Respect its pause flags, connected account IDs, posting scope, timezone, and daily caps. Reconcile pending submissions and scheduled receipts first. Scan the configured folder, prepare and inspect eligible derivatives, and write destination-appropriate captions. In review mode leave new items as drafts; in automatic mode approve only items within the saved scope. Claim each job atomically before submitting it through the selected connector. Save receipts immediately, reconcile uncertain outcomes without blind retries, and verify remote publication separately. Process at most [configured limit] new jobs, skip elapsed slots, and exit after this batch. Report drafts, scheduled times, published links, and connection failures. If empty or paused, do nothing further.

## Pause and resume

An explicit “stop posting” request covers the local task and pending posts at the provider. Pause the task, set the profile pause flag, inspect remotely scheduled items, and pause/cancel those within scope. Keep published history and originals. A local pause alone cannot stop remote posts already accepted by a scheduler; report any remote item you could not stop.

Resume only after the user requests it. Reconcile remote state before filling future slots. Expired credentials block their account; reconnect that account separately without resetting the other accounts or reposting their successful items.
