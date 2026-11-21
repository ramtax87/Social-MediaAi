# Durable local queue

`scripts/queue.py` uses Python's standard library and SQLite. It never calls a social network, uploads a file, authorizes publication, or runs a timer. The agent performs those actions through its selected tools and records results here. Keep one shared database in the private workspace, outside the media source tree and Git repository.

## Scan and plan

Commands below run from the installed skill directory. Replace example absolute paths and returned IDs with real ones. Pass captions in a UTF-8 file, not shell-interpolated text.

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 scan /absolute/media/folder
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 media
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 status
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 list --state draft
```

Scanning hashes content rather than filenames, so renames and exact copies do not create duplicate source entries. It ignores hidden files, symlinks, empty files, unsupported extensions, and files modified within the last ten seconds. Use `--recursive` only when subfolders are in scope. A stable timestamp is a heuristic, not proof a copy has completed: for an active import, wait until its producer finishes or use atomic file moves into the inbox. Inspect the actual media; an extension alone does not validate its contents.

Create a job for one source and one verified account:

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 plan SOURCE_HASH \
  --destination instagram:ACCOUNT_ID \
  --due 2030-01-15T09:00:00+01:00 \
  --prepared /absolute/workspace/prepared/photo.jpg \
  --caption-file /absolute/workspace/captions/photo.txt
```

The date is illustrative: choose an actual future slot. Supply `--metadata-file /absolute/workspace/post-metadata.json` for platform-specific fields such as video title, privacy, audience, or post type. It must be a JSON object with no credentials. Store all fields affecting the social post there so the approved content is unambiguous. Keep ephemeral upload URLs and provider credentials outside the post content.

Use a stable `platform:account-id` destination, not only a display name. One content hash can target several accounts, but the helper deliberately allows only one job per source/account pair. Changing a draft reuses its job ID and clears approval; a submitted job must be reconciled first. Intentional repost campaigns, carousels, and multi-asset slideshows require extending the ledger's data model; do not evade deduplication by inventing a different account ID.

The prepared file must be a separate copy. Approval binds the source hash, derivative bytes, caption, metadata, destination, and due time. Keep files stable until submission. If an original is renamed, scan again so the ledger can find it. If it is changed or removed, investigate before using a stale preparation.

## Approve, claim, and record

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 approve JOB_ID
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 claim JOB_ID --schedule
```

Run `approve` only after an actual per-post approval or the agent has checked the saved automatic-posting scope. The command cannot determine what the user authorized. `claim` uses a transaction so two processes cannot both submit the same job. It validates the current files and emits the exact job payload. `--schedule` permits claiming a future job for a provider's scheduling API; without it, the job must already be due. Stop immediately if claim fails.

After a successful claim, use the selected publishing connector with that exact payload, including metadata. If it requires hosted media, upload only the approved derivative to the chosen host and preserve its content mapping. Do not submit a second time while this job is `submitting`.

When the provider returns a receipt:

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 finish JOB_ID \
  --state scheduled --receipt PROVIDER_POST_ID
```

For immediate publication use `--state published` only when it is confirmed live. For a scheduled post, later query its remote status and transition from `scheduled` to `published` with `finish` and its confirmed receipt/permalink. Local due time passing does not prove publication. Retain account-specific results even if another destination fails.

## Uncertain outcomes and recovery

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 uncertain JOB_ID \
  --reason "Response lost after submitting the request"
```

A crash between submission and saving the receipt leaves `submitting`. Treat it exactly like an uncertain result: query the provider by known ID or inspect that account's recent/scheduled posts. Do not infer failure from an empty first page, delayed indexing, or a timeout.

If the post is found:

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 resolve JOB_ID \
  --state scheduled --receipt FOUND_PROVIDER_POST_ID
```

If the provider establishes that no post was created (or cancellation is confirmed) and retry is appropriate:

```sh
python3 scripts/queue.py --db /absolute/workspace/queue.sqlite3 resolve JOB_ID \
  --verified-absent --evidence "Provider confirms the request was rejected before creation"
```

This returns it to draft and requires fresh approval before another claim. Use evidence from the actual response or remote lookup, not the example text. Known rejection or post-cancellation recovery can use `uncertain` plus this explicit resolution; there is no blind auto-retry command. Leave unresolved outcomes untouched and report them.

The helper prevents common local duplicate submissions. It cannot promise exactly-once remote publication; that depends on provider receipts and reconciliation. Daily caps, slot spacing, profile pause flags, account permissions, media format checks, and credential expiration are enforced by the agent/provider workflow, not this ledger. Read `list --limit 100 --offset 0` in pages for large queues.
