# Connections and publishing

Verified against the official sources below on 2026-11-21. Recheck the chosen provider's current schema, account capabilities, media limits, and access requirements during setup. This is a provider-neutral workflow; Buffer is an optional implementation, not a required subscription.

## Connect one account at a time

Ask which network to connect first. Inspect available connectors before requesting information already available there. For this network only, establish the exact account/Page/channel, publishing route, supported content types, timezone, and the user's posting authorization. Let the owner complete OAuth or the provider's sign-in flow; never ask for a social-media password in chat. Store credentials in the connector or a local secret store, never in the repository or media manifest.

Use an existing authorized connector or scheduler when it meets the task. If none is available, explain that network's direct API requirements or offer an optional scheduler. Do not silently create a paid subscription, public storage bucket, or developer application. A failed connection should not prevent preparing local drafts or using other connected networks.

Verify the connection with a read operation and record the stable account ID plus human-readable name. Then ask whether the user wants to connect another network. Each new destination is a separate choice, even if a provider exposes several accounts under one login. Connecting an account alone does not authorize publishing every file in a folder.

## Network choices

| Network | Account and delivery constraints |
| --- | --- |
| Instagram | Automatic publishing requires a Professional Business or Creator account. Personal accounts need a manual publishing/reminder route. Direct Meta publishing creates a media container, waits for readiness, then publishes it. Choose the login flow before requesting scopes; Instagram Login and Facebook Login use different hosts and permissions. [Meta publishing](https://developers.facebook.com/documentation/instagram-platform/content-publishing), [Buffer account connection options](https://support.buffer.com/en-us/articles/connecting-your-instagram-account-to-buffer-n9Ad6veXsu). |
| Facebook | Distinguish a Page from a personal profile or Group. The direct Page API supports photo uploads and scheduled Page posts; do not assume this grants profile/Group publishing. Confirm Page permissions and Page access token. Buffer requires notification publishing for Groups. [Page photos](https://developers.facebook.com/docs/graph-api/reference/page/photos/), [Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/), [Buffer notification publishing](https://support.buffer.com/en-us/articles/using-notification-publishing-gvZQiMxVa2). |
| TikTok | Prefer an existing approved connector/scheduler. A bespoke Direct Post app requires approved `video.publish` access, creator-information checks and explicit consent; unaudited clients have private-only restrictions. TikTok's developer guidelines exclude an app limited to uploading for its developer/team, so a personal automation script is not a general public-posting workaround. [Direct Post setup](https://developers.tiktok.com/docs/en/content-posting-api-get-started), [developer guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines). |
| YouTube | Direct YouTube Data API uploads support scheduled publication with a future `status.publishAt` on a private, never-published video. Set privacy explicitly. Buffer supports **Shorts only**, up to three minutes, square or portrait, and requires a video; use another verified route for long-form videos. Confirm channel ownership, title, audience and privacy settings. [Video upload](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert), [scheduling semantics](https://developers.google.com/youtube/data/reference/rest/v3/videos#status.publishAt), [Buffer Shorts](https://support.buffer.com/articles/using-youtube-shorts-with-buffer-Jl8iR6jIck). |
| LinkedIn | Choose the member profile or organization explicitly and verify the required permissions/organization role. Direct API image/video posts need a completed media upload and its asset URN before creating a post. Use the current supported LinkedIn API version and supported scheduler/runner for future delivery. [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api). |

For direct Instagram publishing, the verified flow is `POST /{ig-id}/media`, `GET /{container-id}?fields=status_code`, then `POST /{ig-id}/media_publish` with `creation_id`. Image/video URLs must be publicly retrievable for URL-based uploads; JPEG is the direct API's supported image format. Create containers close enough to delivery to respect their current expiry rules. Do not treat a container ID as a published-post ID. Read the current [Meta publishing guide](https://developers.facebook.com/documentation/instagram-platform/content-publishing) before constructing requests; do not hardcode an API version from this reference.

## Optional shared route: Buffer

Buffer provides an official remote MCP server at `https://mcp.buffer.com/mcp`. Prefer its connected tools when available. Typical sequence: `get_account`, `list_channels`, then `get_channel` for the selected destination's schedule and capabilities. The publishing tools include `create_post`, `get_post`, and `list_posts`. Discover actual tool names and schemas in the environment. [Official MCP reference](https://developers.buffer.com/guides/integrations/mcp.html).

### Configure the optional connection in Codex

After the user chooses Buffer and approves the connection, inspect existing MCP entries before adding one. With Codex CLI available, first check `codex mcp --help` and `codex mcp list`. If the endpoint is not already configured, the supported connection commands are:

```sh
codex mcp add buffer --url https://mcp.buffer.com/mcp
codex mcp login buffer
```

Adding the server may already initiate login; run `login` only if authentication is still needed. Let the user complete OAuth. Without CLI access, guide them through Settings → MCP servers → Add server, using the same HTTPS endpoint, then Authenticate. Use an existing plugin connection instead when available. [Official Codex connection instructions](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [Buffer connection guidance](https://developers.buffer.com/guides/integrations/other-ai-tools.html).

Refresh the host's tools if required, then verify identity and select the intended social channel read-only. If no channel exists, guide the user through connecting that social account in Buffer before continuing. A configured endpoint, completed provider login, and connected social channel are separate states. Save the verified state and ask about the next account only after this one is complete or skipped. Set up the media-upload route below before promising unattended local-folder posting.

### Other Buffer interfaces

If using the official CLI instead, install `@bufferapp/cli` only as part of the chosen setup. `buffer init` configures authentication; `buffer doctor`, `buffer channels list`, and `buffer schema describe posts create` support verification. Prepare JSON in a local file, then validate with `buffer posts create --input post.json --dry-run`. Execute the same command without `--dry-run` only within the user's existing posting authorization. JSON files avoid shell-escaping captions. [Official CLI](https://developers.buffer.com/guides/cli.html).

For direct GraphQL, POST JSON to `https://api.buffer.com` with `Content-Type: application/json` and `Authorization: Bearer <token>`. Personal API keys belong to the user's own Buffer account and are created in Settings → API. Read `BUFFER_API_KEY` from the environment rather than embedding it in code. OAuth is available for a distributed application that acts for multiple users; a personal installation does not need its own OAuth client. [Authentication](https://developers.buffer.com/guides/authentication.html).

Use this verified mutation with JSON variables rather than interpolating captions into GraphQL:

```graphql
mutation ScheduleMedia($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post { id dueAt status }
    }
    ... on MutationError { message }
  }
}
```

Example `variables` for a single Instagram photo, with IDs and URL replaced by the verified destination and prepared media:

```json
{
  "input": {
    "channelId": "VERIFIED_CHANNEL_ID",
    "text": "APPROVED_CAPTION",
    "schedulingType": "automatic",
    "mode": "customScheduled",
    "dueAt": "2030-01-15T08:00:00Z",
    "assets": [{"image": {"url": "https://YOUR_MEDIA_HOST/photo.jpg"}}],
    "metadata": {"instagram": {"type": "post", "shouldShareToFeed": true}}
  }
}
```

The sample date is illustrative. Replace `dueAt` with the actual approved future slot, converted to UTC. Use `customScheduled` with the bundled ledger because its approval binds an exact due time. Buffer also supports `addToQueue`, which assigns a slot from the channel's existing schedule; a workflow using flexible queue timing must explicitly authorize that timing and retain the provider's actual assigned slot. Don't silently replace a fixed approved time with a provider-selected slot. `shareNow` is immediate publication and must not be used as a fallback for missed slots. [Scheduling](https://developers.buffer.com/guides/posts-and-scheduling.html).

For video, use an asset entry shaped as `{"video":{"url":"https://YOUR_MEDIA_HOST/clip.mp4"}}`. Instagram single-video feed posts use type `reel`. Facebook requires `metadata.facebook.type`. YouTube requires `metadata.youtube.title` and `categoryId`; also set the agreed privacy and audience fields. Read the current network metadata schema for additional settings. [Video example](https://developers.buffer.com/examples/create-video-post.html), [Instagram metadata](https://developers.buffer.com/types/InstagramPostMetadataInput.html), [Facebook metadata](https://developers.buffer.com/types/FacebookPostMetadataInput.html), [YouTube metadata](https://developers.buffer.com/types/YoutubePostMetadataInput.html).

### Moving local media to a provider

Check whether the selected connector accepts local file uploads. Buffer's API does **not** provide a file-upload endpoint: it needs a direct public HTTPS file URL. Use the user's selected host/CDN and upload only the prepared assets approved for posting. Keep URLs stable through actual publication; expiring signed links and ordinary Drive/Dropbox preview links do not satisfy this requirement. Never expose the complete inbox or assume that committing photos to GitHub is a media-hosting solution. Retain originals locally and record the hosted asset mapping. [Media hosting requirements](https://developers.buffer.com/guides/hosting-media.html).

### Completion, retries, and duplicates

Persist a local attempt record before creating each remote post. Record destination, media hash, caption/payload, slot, and resulting remote ID. Each network is an independent result: a successful Instagram submission must not be repeated because Facebook failed.

Check HTTP status, GraphQL `errors`, and the typed mutation result. HTTP 200 alone is not success. A response can include both a saved post and warnings: preserve a returned post ID and reconcile it before considering any retry. [Error handling](https://developers.buffer.com/guides/error-handling.html).

On timeout, interrupted execution, or an ambiguous response, mark the attempt uncertain. Query the known post ID or search the selected channel's scheduled/sending/sent/error posts by time, exact caption and asset source. Reuse an identified post; do not blindly repeat the create operation. If the remote outcome remains ambiguous, keep it unresolved for review. This is a local duplicate-prevention strategy, not a claim of provider-supported idempotency keys.

For an explicit rate-limit rejection, honor `Retry-After` and defer the job instead of spinning. Use bounded retries for safe reads. Stop and report authentication, disconnected-account, invalid-media and exhausted-quota errors until their cause is corrected. [API rate limits](https://developers.buffer.com/guides/api-limits.html).

Record “scheduled” when the scheduler accepts the item. Mark it published only after the provider confirms actual automatic publication; retain its remote ID and available permalink. A notification/reminder marked “sent” may mean only that a phone reminder was delivered. Never report it as a live social post without checking. [Instagram delivery behavior](https://support.buffer.com/en-us/articles/scheduling-instagram-posts-reels-stories-and-notifications-3XA98S9Q5p).
