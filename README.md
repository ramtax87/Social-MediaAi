# Social-MediaAi

A reusable agent skill that helps you turn a folder of photos and videos into scheduled social posts. Setup happens in plain language, **one social account connection at a time**.

Choose your own platforms, accounts, editing style, and schedule. Instagram, Facebook, TikTok, YouTube, and LinkedIn are documented options; other networks can be added through supported publishing tools.

## Copy this into Codex

You do not need to clone the repository or edit configuration files yourself. Copy this message:

```text
Find the public GitHub repository ramtax87/Social-MediaAi:
https://github.com/ramtax87/Social-MediaAi
Read README.md and START_HERE.md, install its social-media-ai skill,
and guide me through setting up my own social posting automation.
Do the technical setup for me and ask one simple question at a time.
Connect each social account separately. Show me a sample before posting,
and ask for approval before new account permissions, paid services,
external media hosting, or activating live posting. Remember my choices
and approvals. Start the setup now, rather than just explaining it.
```

Or just ask: **“Find ramtax87/Social-MediaAi on GitHub and follow its START_HERE.md to set it up for me.”**

Codex should handle installation, local checks, workspace creation, configuration, and scheduling. You choose your media folder and preferences, sign in to each selected service through its own login page, and approve the concrete posting plan. Account access and provider limits still depend on the services you choose.

## What the guided setup does

1. Checks your computer and available tools, then installs or updates the skill.
2. Asks for the media folder and creates a separate private workspace.
3. Connects your chosen social accounts one at a time.
4. Helps choose cleanup, captions, posting times, and timezone.
5. Shows actual sample media, captions, accounts, and planned times.
6. Asks whether to review each post or allow automatic posting under those rules.
7. Configures and verifies the recurring task, then reports its status and next runs.

If something needs your login or a tool is missing, Codex explains the one next action and saves your progress. It must not say posting is active until the required tools and schedule are verified. You can start with one account and add more later.

## Come back later

Once installed, say:

```text
Use $social-media-ai and continue my saved setup. Reuse my existing
connections and approvals, check what is still missing, and guide me
through the next step.
```

Say **“Pause all my social posting, including posts already queued remotely”** to stop, or **“Show my connected accounts, drafts, and next posting times”** for status. More copyable prompts are in the [prompt guide](skills/social-media-ai/references/prompts.md).

## What is included

- An agent start guide, guided prompts, and precise approval requests.
- Automatic local workspace setup and prerequisite checks, with saved progress.
- Photo cleanup instructions for your agent's image editor.
- A video conversion/cleanup helper using FFmpeg.
- A local queue that tracks content hashes, approval, submission, and receipts to reduce duplicate posts.
- Publishing guidance for existing connectors, an optional Buffer route, and official platform APIs.
- Recurring-task instructions, pause/resume handling, and recovery after uncertain submissions.

## What you need

A skill-capable agent with local file access and Python 3.10+. Video processing additionally needs FFmpeg and FFprobe on your PATH; photo enhancement needs an image editing tool in your agent. Publishing needs a compatible connector or official API access for each selected account. Some account types, formats, permissions, or provider plans limit what can be published automatically.

**Installing the skill does not connect accounts or start posting.** Your agent completes those steps with you. The Python helpers handle local media and bookkeeping; they do not contain a built-in social publisher or scheduler. A provider scheduler or recurring agent task must be configured for unattended work. Local-folder tasks need a running machine with access to that folder. Keep credentials and personal media outside this repository.

## For developers

After cloning, run `python3 scripts/install.py`. Identical installations are reused. For an updated version, `python3 scripts/install.py --update` preserves the previous skill in a backup before replacement. Use `--destination /path/to/skills` for a custom location, or `--check` to inspect installation status. The instructions follow the [agent skill format](https://learn.chatgpt.com/docs/build-skills); each host needs its own tools and permissions.

The installable skill is [skills/social-media-ai](skills/social-media-ai/SKILL.md). Supporting references explain the workflow and helper commands. Run the local tests with:

```sh
python3 -m unittest discover -s tests -v
```

Tests use local fixtures and mocks; they do not post to real accounts. Live publishing must be verified during the user's own authorized connection setup.
