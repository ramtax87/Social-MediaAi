# Start the user's setup

This is the agent runbook for someone who asks you to find, install, or set up Social-MediaAi. They should only need to answer simple questions and complete their own logins. Perform the technical work available in your environment; don't hand them a list of commands as the finished result.

## 1. Obtain and load the skill

Verify that you are using the public repository `ramtax87/Social-MediaAi` at `https://github.com/ramtax87/Social-MediaAi`. Read its files through a connected GitHub tool or download/clone it locally. Do not confuse it with a similarly named project. Use an existing checkout when available and preserve local changes.

Read [the skill](skills/social-media-ai/SKILL.md) and [the setup runbook](skills/social-media-ai/references/setup.md). If the host has a skill installer, install `skills/social-media-ai` from this repository with it. Otherwise, after inspecting the local installer, run:

```sh
python3 scripts/install.py
```

Use the available Python 3.10+ interpreter (`python3`, `python`, or `py -3` as appropriate). The installer reports the destination; an identical existing installation is reused. For a requested update, inspect the differences and run `python3 scripts/install.py --update`; it preserves the old version in a backup. Existing unrelated local customizations must be kept or reconciled, not silently discarded. If skill discovery has not refreshed, read the installed `SKILL.md` directly and continue the current setup. Only ask for an app restart if a specific tool actually requires it.

## 2. Check the environment and create the workspace

Inspect available local execution, image editing, connected publishing tools, and scheduling tools. Detect the OS, Python, FFmpeg, and FFprobe without installing anything yet. Read existing setup/profile state before asking questions; don't scan unrelated personal folders to find it. If there is no known profile, ask for the media folder first. Suggest `~/Social-MediaAi-workspace` as the private working folder if it is outside the source folder and repository.

Use the installed helper to create the workspace and run local checks, following [setup.md](skills/social-media-ai/references/setup.md). The agent writes configuration from the user's answers. The user should not need to hand-edit JSON. Missing system software needs a concrete installation proposal before it is installed unless already authorized; missing connected tools need a supported connection route. The helper cannot inspect live accounts or prove an automation exists.

## 3. Guide the decisions and do the work

Follow [setup.md](skills/social-media-ai/references/setup.md) and [approvals.md](skills/social-media-ai/references/approvals.md). Ask one short question at a time. Finish or skip each account connection before starting the next. Resolve media editing, upload access, caption style, posting cadence, timezone, and review mode. Reuse information already supplied.

Use the user's answers immediately: create directories, save settings, inspect media, produce a sample, and verify connections read-only. Ask the user only for actions you cannot perform for them, such as signing in, choosing an account, granting a new permission, selecting a cost-bearing service, or approving a posting plan. Explain the reason and exact scope of each approval request. Keep progress locally so another turn can continue where this one stopped.

## 4. Preview, activate, and verify

Show real prepared media and captions, the exact accounts, and the next posting dates with timezone offsets. Do not substitute example captions or fictitious post links for a sample. Record the selected approval mode and scope. Set up the real recurring task through the host's tools, and verify its saved ID and access to the same workspace and connections. Use [scheduling.md](skills/social-media-ai/references/scheduling.md).

In review mode, new posts stay in drafts; the recurring workflow may submit the exact jobs already approved by the user. In automatic mode, it can prepare and submit new items within the saved scope. Actual external publication still requires the selected publishing tool. A complete profile or successful local check alone does not activate anything.

Finish with a short status: workspace location, verified accounts, review/automatic mode, scheduler ID and next runs if active, and the single next action if anything is blocked. Give the user the [resume and pause prompts](skills/social-media-ai/references/prompts.md). Do not end with a generic “you still need to configure it” when you can perform the remaining setup. If a login/approval or unavailable capability blocks a step, save progress, state the exact missing action, and continue independent preparation where possible.
