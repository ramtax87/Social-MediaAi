#!/usr/bin/env python3
"""Local media ledger. No network, publishing, daemon, or automatic retries."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time


EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif",
              ".tif", ".tiff", ".bmp", ".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def now():
    return datetime.now(timezone.utc).isoformat()


def due_time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("due must be an ISO timestamp with UTC offset") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("due must include a UTC offset; resolve daylight-saving time first")
    return result.astimezone(timezone.utc).isoformat()


def hash_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular, non-symlink file: {path}")
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError(f"file changed during reading: {path}")
    return digest.hexdigest()


def file_path(value):
    path = Path(value).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular, non-symlink file: {path}")
    return str(path.resolve())


def connect(path):
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise ValueError("database must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER NOT NULL,
            discovered_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, media_id TEXT NOT NULL REFERENCES media(id),
            destination TEXT NOT NULL, due TEXT NOT NULL, prepared TEXT NOT NULL,
            prepared_hash TEXT NOT NULL, caption_file TEXT NOT NULL,
            caption TEXT NOT NULL, caption_hash TEXT NOT NULL,
            metadata_file TEXT, metadata TEXT NOT NULL DEFAULT '{}', metadata_hash TEXT,
            fingerprint TEXT NOT NULL, approval TEXT, state TEXT NOT NULL,
            receipt TEXT, note TEXT, updated_at TEXT NOT NULL,
            UNIQUE(media_id, destination)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
            happened_at TEXT NOT NULL, state TEXT NOT NULL, detail TEXT NOT NULL
        );
    """)
    columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
    for name, definition in (("metadata_file", "TEXT"), ("metadata", "TEXT NOT NULL DEFAULT '{}'"),
                             ("metadata_hash", "TEXT")):
        if name not in columns:
            db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
    return db


@contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def event(db, job_id, state, detail):
    db.execute("INSERT INTO events(job_id,happened_at,state,detail) VALUES(?,?,?,?)",
               (job_id, now(), state, detail))


def job_dict(row):
    result = dict(row)
    result["metadata"] = json.loads(result["metadata"])
    return result


def get_job(db, job_id):
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        raise ValueError("unknown job id; use list")
    return job_dict(row)


def validate_files(db, job):
    source = db.execute("SELECT path FROM media WHERE id=?", (job["media_id"],)).fetchone()[0]
    if hash_file(source) != job["media_id"]:
        raise ValueError("source changed; rescan and prepare a new job")
    if hash_file(job["prepared"]) != job["prepared_hash"]:
        raise ValueError("prepared media changed; re-plan and approve again")
    if hash_file(job["caption_file"]) != job["caption_hash"]:
        raise ValueError("caption changed; re-plan and approve again")
    if job.get("metadata_file") and hash_file(job["metadata_file"]) != job["metadata_hash"]:
        raise ValueError("platform metadata changed; re-plan and approve again")


def scan(db, args):
    folder = Path(args.folder).expanduser()
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("scan needs a non-symlink directory")
    folder = folder.resolve()
    if args.min_age < 0:
        raise ValueError("min-age cannot be negative")
    candidates = []
    for root, directories, files in os.walk(folder, followlinks=False):
        directories[:] = sorted(d for d in directories if not d.startswith(".")
                                and not (Path(root) / d).is_symlink())
        for name in sorted(files):
            path = Path(root) / name
            if not name.startswith(".") and path.suffix.lower() in EXTENSIONS and not path.is_symlink():
                candidates.append(path)
        if not args.recursive:
            break
    added, skipped = [], 0
    for path in candidates:
        try:
            size = path.stat().st_size
            if not size or time.time() - path.stat().st_mtime < args.min_age:
                skipped += 1
                continue
            media_id = hash_file(path)
            with transaction(db):
                existing = db.execute("SELECT path FROM media WHERE id=?", (media_id,)).fetchone()
                if existing is None:
                    db.execute("INSERT INTO media VALUES(?,?,?,?)", (media_id, str(path), size, now()))
                    added.append({"id": media_id, "path": str(path)})
                elif existing[0] != str(path):
                    try:
                        existing_matches = hash_file(existing[0]) == media_id
                    except (OSError, ValueError):
                        existing_matches = False
                    if not existing_matches:
                        db.execute("UPDATE media SET path=? WHERE id=?", (str(path), media_id))
        except (OSError, ValueError):
            skipped += 1
    return {"added": added[:100], "added_count": len(added), "skipped": skipped,
            "total_media": db.execute("SELECT COUNT(*) FROM media").fetchone()[0]}


def plan(db, args):
    destination = args.destination.strip()
    if not destination:
        raise ValueError("destination needs a stable platform/account identifier")
    due = due_time(args.due)
    prepared, caption_file = file_path(args.prepared), file_path(args.caption_file)
    source = db.execute("SELECT * FROM media WHERE id=?", (args.media_id,)).fetchone()
    if source is None:
        raise ValueError("unknown media id; scan and use media first")
    if prepared == source["path"] or os.path.samefile(prepared, source["path"]):
        raise ValueError("prepared media must be a separate copy; preserve the original")
    if Path(caption_file).stat().st_size > 100_000:
        raise ValueError("caption file exceeds 100 KB")
    caption_hash = hash_file(caption_file)
    caption = Path(caption_file).read_text(encoding="utf-8")
    if hashlib.sha256(caption.encode("utf-8")).hexdigest() != caption_hash:
        # Reading in text mode can normalize CRLF; snapshot the actual UTF-8 bytes.
        caption = Path(caption_file).read_bytes().decode("utf-8")
    if hashlib.sha256(caption.encode("utf-8")).hexdigest() != caption_hash:
        raise ValueError("caption changed during reading")
    metadata_file, metadata_hash, metadata = None, None, {}
    if args.metadata_file:
        metadata_file = file_path(args.metadata_file)
        if Path(metadata_file).stat().st_size > 100_000:
            raise ValueError("metadata file exceeds 100 KB")
        metadata_hash = hash_file(metadata_file)
        metadata = json.loads(Path(metadata_file).read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a JSON object")
    payload = {"media_id": args.media_id, "destination": destination, "due": due,
               "prepared": prepared, "prepared_hash": hash_file(prepared),
               "caption_file": caption_file, "caption": caption, "caption_hash": caption_hash,
               "metadata_file": metadata_file, "metadata_hash": metadata_hash,
               "metadata": json.dumps(metadata, ensure_ascii=False, sort_keys=True, allow_nan=False)}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    job_id = hashlib.sha256((args.media_id + "\0" + destination).encode()).hexdigest()[:24]
    with transaction(db):
        validate_files(db, payload)
        existing = db.execute("SELECT state FROM jobs WHERE id=?", (job_id,)).fetchone()
        if existing and existing[0] not in {"draft", "approved"}:
            raise ValueError("job already submitted; reconcile its receipt before changing anything")
        values = dict(payload, id=job_id, fingerprint=fingerprint, updated_at=now())
        db.execute("""INSERT INTO jobs(id,media_id,destination,due,prepared,prepared_hash,
                      caption_file,caption,caption_hash,metadata_file,metadata,metadata_hash,
                      fingerprint,state,updated_at)
                      VALUES(:id,:media_id,:destination,:due,:prepared,:prepared_hash,
                      :caption_file,:caption,:caption_hash,:metadata_file,:metadata,:metadata_hash,
                      :fingerprint,'draft',:updated_at)
                      ON CONFLICT(id) DO UPDATE SET due=excluded.due,prepared=excluded.prepared,
                      prepared_hash=excluded.prepared_hash,caption_file=excluded.caption_file,
                      caption=excluded.caption,caption_hash=excluded.caption_hash,
                      metadata_file=excluded.metadata_file,metadata=excluded.metadata,
                      metadata_hash=excluded.metadata_hash,
                      fingerprint=excluded.fingerprint,approval=NULL,state='draft',
                      receipt=NULL,note=NULL,updated_at=excluded.updated_at""", values)
        event(db, job_id, "draft", "planned; prior approval cleared")
    return get_job(db, job_id)


def transition(db, args):
    with transaction(db):
        job = get_job(db, args.job_id)
        state, receipt, note, approval = job["state"], job["receipt"], job["note"], job["approval"]
        if args.command == "approve":
            if state not in {"draft", "approved"}:
                raise ValueError("only draft jobs can be approved")
            validate_files(db, job)
            state, approval, note = "approved", job["fingerprint"], "approved prepared media, caption, destination, and due time"
        elif args.command == "claim":
            if state != "approved" or approval != job["fingerprint"]:
                raise ValueError("job is not approved, already claimed, or requires reconciliation")
            validate_files(db, job)
            future = datetime.fromisoformat(job["due"]) > datetime.now(timezone.utc)
            if future and not args.schedule:
                raise ValueError("job is not due; use --schedule only for a future provider schedule")
            if args.schedule and not future:
                raise ValueError("provider schedule is already past; re-plan or publish when due")
            state, note = "submitting", "claimed for provider scheduling" if args.schedule else "claimed for publication"
        elif args.command == "finish":
            allowed = state == "submitting" or (state == "scheduled" and args.state == "published")
            if not allowed:
                raise ValueError("finish needs a submitting job (or scheduled -> published)")
            state, receipt, note = args.state, args.receipt.strip(), "provider receipt confirmed"
            if not receipt:
                raise ValueError("a provider receipt is required")
        elif args.command == "uncertain":
            if state not in {"submitting", "scheduled"}:
                raise ValueError("only submitted jobs can become uncertain")
            state, note = "uncertain", args.reason.strip()
            if not note:
                raise ValueError("describe the ambiguous result")
        elif args.command == "resolve":
            if state not in {"submitting", "uncertain"}:
                raise ValueError("only submitting or uncertain jobs need reconciliation")
            if args.verified_absent:
                if not args.evidence or not args.evidence.strip() or args.state or args.receipt:
                    raise ValueError("verified-absent requires evidence and no state/receipt")
                state, approval, receipt, note = "draft", None, None, "verified absent: " + args.evidence.strip()
            else:
                if not args.state or not args.receipt or not args.receipt.strip():
                    raise ValueError("resolution requires a state and provider receipt")
                state, receipt, note = args.state, args.receipt.strip(), "reconciled against provider"
        db.execute("UPDATE jobs SET state=?,receipt=?,note=?,approval=?,updated_at=? WHERE id=?",
                   (state, receipt, note, approval, now(), args.job_id))
        event(db, args.job_id, state, json.dumps({"note": note, "receipt": receipt}, ensure_ascii=False))
    return get_job(db, args.job_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="persistent SQLite ledger outside the source/publishing repo")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("scan", help="register stable media; skip hidden files and symlinks")
    command.add_argument("folder")
    command.add_argument("--recursive", action="store_true")
    command.add_argument("--min-age", type=float, default=10, help="minimum unchanged age in seconds (default: 10)")
    for name in ("media", "list"):
        command = commands.add_parser(name)
        command.add_argument("--limit", type=int, default=100)
        command.add_argument("--offset", type=int, default=0)
        if name == "list":
            command.add_argument("--state")
    commands.add_parser("status")
    command = commands.add_parser("plan")
    command.add_argument("media_id")
    for name in ("destination", "due", "prepared", "caption-file"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--metadata-file", help="optional JSON object of platform fields, bound to approval")
    for name in ("approve", "claim", "finish", "uncertain", "resolve"):
        command = commands.add_parser(name)
        command.add_argument("job_id")
        if name == "claim":
            command.add_argument("--schedule", action="store_true", help="claim before due for a provider's future schedule")
        if name in {"finish", "resolve"}:
            command.add_argument("--state", choices=("scheduled", "published"), required=name == "finish")
            command.add_argument("--receipt", required=name == "finish")
        if name == "uncertain":
            command.add_argument("--reason", required=True)
        if name == "resolve":
            command.add_argument("--verified-absent", action="store_true")
            command.add_argument("--evidence")
    args = parser.parse_args(argv)
    db = None
    try:
        db = connect(args.db)
        if args.command == "scan":
            result = scan(db, args)
        elif args.command == "plan":
            result = plan(db, args)
        elif args.command in {"media", "list"}:
            if not 1 <= args.limit <= 500 or args.offset < 0:
                raise ValueError("limit must be 1..500 and offset cannot be negative")
            table = "media" if args.command == "media" else "jobs"
            where = " WHERE state=?" if args.command == "list" and args.state else ""
            values = [args.state] if where else []
            result = [(dict(row) if args.command == "media" else job_dict(row)) for row in db.execute(
                "SELECT * FROM " + table + where + " ORDER BY rowid LIMIT ? OFFSET ?",
                values + [args.limit, args.offset])]
        elif args.command == "status":
            result = {"media": db.execute("SELECT COUNT(*) FROM media").fetchone()[0],
                      "jobs": {row[0]: row[1] for row in db.execute("SELECT state,COUNT(*) FROM jobs GROUP BY state")},
                      "note": "Local ledger only. Submitting/uncertain jobs require provider reconciliation."}
        else:
            result = transition(db, args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
