# Conversation and local profile

Use short steps a nontechnical person can answer. Read back the current choice, perform the work, then ask the next missing question. Do not make the user fill out a five-platform questionnaire or paste credentials.

## Suggested progression

1. “Which folder should I take your photos and videos from?” Check that the runtime can read it. Ask whether subfolders count. Choose a separate private workspace for derivatives, captions, the profile, and `queue.sqlite3`.
2. “Which social account would you like to connect first?” Examples can include Instagram, Facebook, TikTok, YouTube, LinkedIn, or another network. Don't presume an account or platform from the example.
3. Discover that platform's connected tools. If necessary, explain the supported login route and let the user complete its consent flow. Ask for the intended account/page/channel if more than one is visible. Verify its immutable ID and display name read-only; record the allowed post types and whether it supports direct or notification-only publishing.
4. “Would you like to connect another account, or continue with this one?” Finish or skip the current connection before proceeding. For a multi-network scheduler, connecting the provider is one step; selecting and authorizing each downstream social account still happens separately. Never choose every returned channel automatically.
5. “When should I post, and in which timezone?” Capture days, local times, per-account frequency, maximum posts per day, and a bounded batch size. Ask rather than assuming the agent's own timezone. Resolve daylight-saving gaps or ambiguous times explicitly.
6. “How should the pictures, videos, and captions look?” A useful suggestion is natural cleanup, preserved faces/products, the user's language, short factual captions, and no added music. Record exclusions and whether video trimming, crops, generated backgrounds, or slideshows are wanted.
7. Prepare the sample batch. If the user hasn't already chosen, offer review-before-posting or automatic posting from the agreed folder under the shown rules. Store the choice and authorized scope once. Don't reconnect or reapprove a connection that is already covered by the session.

## Private workspace

Copy [profile.example.json](../assets/profile.example.json) into the chosen workspace and fill it with actual answers. Its `null` values intentionally mean “not configured.” It is a guide for the agent, not an executable daemon configuration. Missing schedule/authorization means prepare drafts until resolved.

Keep these locally, outside the public skill checkout:

```text
my-social-workspace/
  profile.json
  queue.sqlite3
  prepared/
  captions/
  previews/
```

Each `connections` entry should have a local connection key, platform, connector/provider, stable account ID, display name, supported formats, and status. Store a reference to credentials (connector name or environment-variable name), never the credential itself. Add only accounts the user selected. If a separate media host is necessary, explain that files will be accessible to that host and the publishing service and configure that connection separately as well.

Verify a new connection by reading identity/capabilities and preparing a draft locally. Do not publish a “test post” merely to check credentials. Paid plans or new services are choices, not default prerequisites; explain an actual cost before the user subscribes.

## Example exchange

User: “Set this up for my business.”

Agent: “Which folder contains the pictures and videos you want to use?”

After inspecting the chosen folder: “Which social account should we connect first?”

After a successful Instagram connection: “Instagram @your-account is connected. Would you like to add another account or set the schedule?”

Do useful independent preparation while waiting for answers. If a connection cannot be completed, leave its state blocked and continue with the user's other choices. Do not create active posting schedules in a general installation session before the user has selected destinations and authorized their posting scope.
