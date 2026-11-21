# Conversation and local profile

Use short steps a nontechnical person can answer. Read back the current choice, perform the work, then ask the next missing question. Do not make the user fill out a five-platform questionnaire or paste credentials.

## Perform the local setup

Inspect the runtime first: local file access, Python 3.10+, FFmpeg/FFprobe, an image editing tool, publishing connectors, and a scheduler. Use the user's existing profile if known. Ask for the folder before creating a new workspace. Suggest a separate directory such as `~/Social-MediaAi-workspace`; avoid the source folder, the repository, or the installed skill directory.

Run these from the installed skill directory with actual absolute paths (the user does not need to type them):

```sh
python3 scripts/setup.py init --workspace /absolute/private/workspace --source /absolute/media/folder
python3 scripts/setup.py doctor --workspace /absolute/private/workspace
```

Add `--recursive` only when requested. `init` creates private state and derivative folders with posting paused and review mode enabled. Repeating it resumes an existing profile without resetting choices. `doctor` performs read-only local checks and lists next steps; its success cannot verify a remote account, image editor, or real scheduled task. Follow the conversation progression below instead of asking about every reported check at once; skip optional video dependencies in a photos-only workflow. A missing dependency should produce one actionable installation/connection proposal; after approval, perform the available setup yourself and recheck. Do not tell the user to edit JSON or run commands you can execute.

Save answers to `profile.json` as they arrive, preserving unrelated fields. Save the next incomplete step and any specific blocker in a local `setup-progress.json` so another chat can resume; use paths and nonsecret facts only. An interrupted setup remains paused. If the user asks to continue and the workspace is unknown, ask for its path rather than searching unrelated private directories.

## Suggested progression

1. “Which folder should I take your photos and videos from?” Check that the runtime can read it. Ask whether subfolders count. Choose a separate private workspace for derivatives, captions, the profile, and `queue.sqlite3`.
2. “Which social account would you like to connect first?” Examples can include Instagram, Facebook, TikTok, YouTube, LinkedIn, or another network. Don't presume an account or platform from the example.
3. Discover that platform's connected tools. If necessary, explain the supported login route and let the user complete its consent flow. Ask for the intended account/page/channel if more than one is visible. Verify its immutable ID and display name read-only; record the allowed post types and whether it supports direct or notification-only publishing. Read [publishing.md](publishing.md) to configure the chosen route; it includes an optional Codex connection recipe.
4. “Would you like to connect another account, or continue with this one?” Finish or skip the current connection before proceeding. For a multi-network scheduler, connecting the provider is one step; selecting and authorizing each downstream social account still happens separately. Never choose every returned channel automatically.
5. “When should I post, and in which timezone?” Capture days, local times, per-account frequency, maximum posts per day, and a bounded batch size. Ask rather than assuming the agent's own timezone. Resolve daylight-saving gaps or ambiguous times explicitly.
6. “How should the pictures, videos, and captions look?” A useful suggestion is natural cleanup, preserved faces/products, the user's language, short factual captions, and no added music. Record exclusions and whether video trimming, crops, generated backgrounds, or slideshows are wanted.
7. Prepare the sample batch. If the user hasn't already chosen, offer review-before-posting or automatic posting from the agreed folder under the shown rules. Store the choice and authorized scope once. Don't reconnect or reapprove a connection that is already covered by the session.

## Private workspace

The helper initializes [profile.example.json](../assets/profile.example.json) in the chosen workspace. Fill it with actual answers. Its `null` values intentionally mean “not configured.” It is a guide for the agent, not an executable daemon configuration. Missing schedule/authorization means prepare drafts until resolved.

Keep these locally, outside the public skill checkout:

```text
my-social-workspace/
  profile.json
  queue.sqlite3
  prepared/
  captions/
  previews/
```

Each `connections` entry should use `key`, `platform`, `provider`, `account_id`, `display_name`, `supported_formats`, and `status` fields. Add `delivery_mode` (automatic or notification), `verified_at`, and a `credential_ref` only where useful. Store a reference to credentials (connector name or environment-variable name), never the credential itself. Add only accounts the user selected. A saved connection status is historical; recheck live access before activation. If a separate media host is necessary, explain that files will be accessible to that host and the publishing service and configure that connection separately as well.

Verify a new connection by reading identity/capabilities and preparing a draft locally. Do not publish a “test post” merely to check credentials. Paid plans or new services are choices, not default prerequisites; explain an actual cost before the user subscribes.

## Example exchange

User: “Set this up for my business.”

Agent: “Which folder contains the pictures and videos you want to use?”

After inspecting the chosen folder: “Which social account should we connect first?”

After a successful Instagram connection: “Instagram @your-account is connected. Would you like to add another account or set the schedule?”

Do useful independent preparation while waiting for answers. If a connection cannot be completed, leave its state blocked and continue with the user's other choices. Do not create active posting schedules in a general installation session before the user has selected destinations and authorized their posting scope.

## Verify the complete path before activation

Resolve each of these with actual tool results: a readable source and writable shared workspace; a real checked photo/video derivative or the user's explicit original-media choice; the intended account's read-only identity and publishing capability; a supported local upload or approved media-host route; exact prepared jobs; the chosen posting scope; and a scheduler that can access the same files and credentials unattended. If the provider/host requires human confirmation for every write, explain that review remains required rather than promising full automation.

After the preview and the necessary approval, configure the recurring task, record its returned ID, and verify its saved schedule. Change `paused` only when the configured mode and activation are authorized. Report “setup saved, awaiting [specific action]” if blocked, or “active in [mode]” with verified evidence. Do not claim a profile file or `doctor` result alone means posting is active.
