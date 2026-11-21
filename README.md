# Social-MediaAi

A reusable agent skill that helps you turn a folder of photos and videos into scheduled social posts. Setup happens in plain language, **one social account connection at a time**.

Choose your own platforms, accounts, editing style, and schedule. Instagram, Facebook, TikTok, YouTube, and LinkedIn are documented options; other networks can be added through supported publishing tools.

## Start here

Give your agent this message:

```text
Install the social-media-ai skill from
https://github.com/ramtax87/Social-MediaAi/tree/main/skills/social-media-ai
Then help me set it up. Ask one question at a time and connect each
social account separately. Start by asking which media folder to use.
```

Or clone this repository and run `python3 scripts/install.py`. This copies the skill to your local Codex skills folder without replacing an existing installation. In hosts with another skill location, pass `--destination /path/to/skills`. The instructions follow the [agent skill format](https://learn.chatgpt.com/docs/build-skills); each host still needs its own tools and permissions.

Once installed, say:

```text
Use $social-media-ai to clean up my pictures and videos and post them
regularly. Help me choose the schedule and connect my accounts one by one.
```

You can start with one account and add more later. The agent prepares a sample, then follows your choice of reviewing each post or allowing automatic posting under your agreed rules.

## What is included

- Guided folder, account, editing, caption, and schedule setup.
- Photo cleanup instructions for your agent's image editor.
- A video conversion/cleanup helper using FFmpeg.
- A local queue that tracks content hashes, approval, submission, and receipts to reduce duplicate posts.
- Publishing guidance for existing connectors, an optional Buffer route, and official platform APIs.
- Recurring-task instructions, pause/resume handling, and recovery after uncertain submissions.

## What you need

A skill-capable agent with local file access and Python 3.10+. Video processing additionally needs FFmpeg and FFprobe on your PATH; photo enhancement needs an image editing tool in your agent. Publishing needs a compatible connector or official API access for each selected account. Some account types, formats, permissions, or provider plans limit what can be published automatically.

**Installing the skill does not connect accounts or start posting.** Your agent completes those steps with you. The Python helpers handle local media and bookkeeping; they do not contain a built-in social publisher or scheduler. A provider scheduler or recurring agent task must be configured for unattended work. Local-folder tasks need a running machine with access to that folder. Keep credentials and personal media outside this repository.

## For developers

The installable skill is [skills/social-media-ai](skills/social-media-ai/SKILL.md). Supporting references explain the workflow and helper commands. Run the local tests with:

```sh
python3 -m unittest discover -s tests -v
```

Tests use local fixtures and mocks; they do not post to real accounts. Live publishing must be verified during the user's own authorized connection setup.
