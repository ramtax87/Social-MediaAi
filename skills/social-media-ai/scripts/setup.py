#!/usr/bin/env python3
"""Initialize a private local workspace or check it without contacting services."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SKILL = Path(__file__).resolve().parents[1]
FOLDERS = ("prepared", "captions", "previews")
DAYS = {"mo", "tu", "we", "th", "fr", "sa", "su", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


def object_value(value):
    return value if isinstance(value, dict) else {}


def read_profile(workspace):
    path = workspace / "profile.json"
    if path.is_symlink():
        raise ValueError("profile.json must not be a symlink.")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Cannot read profile.json as JSON; preserve it and inspect the local file.") from exc
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError("Expected a schema_version 1 profile object; preserve the existing file.")
    return profile


def paths(workspace, source):
    workspace, source = Path(workspace).expanduser(), Path(source).expanduser()
    if workspace.is_symlink() or source.is_symlink():
        raise ValueError("Choose real source and workspace directories, not symlinks.")
    if not source.is_dir():
        raise ValueError("Source folder does not exist or is not a directory.")
    with os.scandir(source) as entries:
        next(entries, None)
    workspace, source = workspace.resolve(), source.resolve()
    if workspace == source or workspace.is_relative_to(source) or source.is_relative_to(workspace):
        raise ValueError("Source and workspace must be separate, non-nested directories.")
    protected = [SKILL]
    protected += [parent for parent in (*SKILL.parents, workspace, *workspace.parents) if (parent / ".git").exists()]
    checkout = SKILL.parent.parent
    if (SKILL.parent.name == "skills" and (checkout / "scripts" / "install.py").is_file()
            and (checkout / "README.md").is_file()):
        protected.append(checkout)  # GitHub ZIP downloads have no .git directory.
    if any(workspace == root or workspace.is_relative_to(root) for root in protected):
        raise ValueError("Keep the private workspace outside the repository and installed skill directory.")
    return workspace, source


def initialize(workspace, source, recursive=False):
    workspace, source = paths(workspace, source)
    profile_path = workspace / "profile.json"
    if profile_path.exists() or profile_path.is_symlink():
        profile = read_profile(workspace)
        if profile.get("source_folder") != str(source) or profile.get("workspace_folder") != str(workspace):
            raise ValueError("Existing profile uses a different source or workspace. Review the change before updating it.")
        return {"status": "resumed", "workspace": str(workspace),
                "note": "Existing profile and queue preserved, including saved recursion and authorization settings.",
                "next_command": [sys.executable, str(Path(__file__).resolve()), "doctor", "--workspace", str(workspace)]}
    if workspace.exists() and not workspace.is_dir():
        raise ValueError("Workspace path is not a directory.")
    for name in (*FOLDERS, "queue.sqlite3"):
        child = workspace / name
        if child.exists() or child.is_symlink():
            raise ValueError("Workspace has existing runtime files without a profile; inspect them before initializing.")
    profile = json.loads((SKILL / "assets" / "profile.example.json").read_text(encoding="utf-8"))
    profile.update(source_folder=str(source), workspace_folder=str(workspace), recursive=recursive, paused=True)
    profile["authorization"] = {"mode": "review", "recorded_at": None, "scope": None}
    workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in FOLDERS:
        (workspace / name).mkdir(mode=0o700)
    with os.fdopen(os.open(profile_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as stream:
        json.dump(profile, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    spec = importlib.util.spec_from_file_location("social_media_queue", SKILL / "scripts" / "queue.py")
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    database = workspace / "queue.sqlite3"
    ledger.connect(database).close()
    if os.name != "nt":
        database.chmod(0o600)
    return {"status": "initialized", "workspace": str(workspace), "paused": True,
            "authorization_mode": "review", "note": "No accounts connected, media uploaded, or schedules activated.",
            "next_command": [sys.executable, str(Path(__file__).resolve()), "doctor", "--workspace", str(workspace)]}


def doctor(workspace):
    workspace = Path(workspace).expanduser().resolve()
    checks, steps = [], []

    def check(name, success, detail, action, optional=False):
        checks.append({"name": name, "status": "ok" if success else "optional_missing" if optional else "needs_attention",
                       "detail": detail})
        if not success:
            steps.append({"id": name, "action": action})

    check("python", sys.version_info >= (3, 10), "Python 3.10 or newer is required.", "Install a supported Python version.")
    profile, error = {}, None
    try:
        profile = read_profile(workspace)
    except ValueError as exc:
        error = str(exc)
    check("profile", error is None, error or "Profile schema is readable.", "Initialize or repair the private profile without overwriting saved settings.")
    source = profile.get("source_folder")
    valid_paths = False
    if isinstance(source, str) and source:
        try:
            resolved_workspace, _ = paths(workspace, source)
            valid_paths = profile.get("workspace_folder") == str(resolved_workspace)
        except (OSError, ValueError):
            pass
    check("folders", valid_paths, "Source must be readable and separate from the workspace and skill checkout.",
          "Choose an accessible source folder and separate private workspace; confirm before changing a saved source.")
    runtime_dirs = all((workspace / name).is_dir() and not (workspace / name).is_symlink() for name in FOLDERS)
    check("runtime_folders", runtime_dirs, "Prepared media, captions, and previews use local workspace directories.",
          "Create missing workspace directories after inspecting any conflicting files.")
    ledger_ok = False
    database = workspace / "queue.sqlite3"
    if database.is_file() and not database.is_symlink():
        try:
            with database.open("rb") as stream:
                ledger_ok = stream.read(16) == b"SQLite format 3\x00"
        except OSError:
            pass
    check("queue", ledger_ok, "Queue database header is checked; no database writes or migrations are performed.",
          "Restore the existing queue if lost; reconcile remote posts before creating a replacement ledger.")
    for name in ("ffmpeg", "ffprobe"):
        check(name, shutil.which(name) is not None, "Needed only for local video processing.",
              f"If videos are selected, offer to install {name} through the user's normal package manager.", optional=True)
    timezone = profile.get("timezone")
    timezone_ok = False
    if isinstance(timezone, str) and timezone:
        try:
            ZoneInfo(timezone)
            timezone_ok = True
        except (ValueError, ZoneInfoNotFoundError):
            pass
    check("timezone", timezone_ok, "A resolvable IANA timezone is required for recurring local times.",
          "Ask for the posting timezone; if its name is valid but unavailable, install timezone data for this Python environment.")
    connections = profile.get("connections")
    connections = connections if isinstance(connections, list) else []
    summaries = []
    for index, entry in enumerate(connections):
        entry = object_value(entry)
        safe = {key: entry[key][:240] for key in ("platform", "account_id", "display_name") if isinstance(entry.get(key), str)}
        safe.update(index=index, live_status="not_checked")
        formats = entry.get("supported_formats")
        safe["supported_formats"] = [value[:80] for value in formats if isinstance(value, str)][:20] if isinstance(formats, list) else []
        summaries.append(safe)
    identity_ok = bool(summaries) and all(item.get("platform") and item.get("account_id") for item in summaries)
    check("account_records", identity_ok, "Saved identity fields do not verify a live connection or publishing permission.",
          "Ask which account to connect first, then complete or skip each connection separately.")
    captions, editing = object_value(profile.get("captions")), object_value(profile.get("editing"))
    style_ok = all(isinstance(value, str) and bool(value.strip()) for value in (captions.get("language"), captions.get("tone"), editing.get("style")))
    check("style", style_ok, "Language, caption tone, and editing style must be chosen.",
          "Ask for caption language and offer natural cleanup with a short factual caption style.")
    schedule = object_value(profile.get("schedule"))
    days, times = schedule.get("days"), schedule.get("local_times")
    days_ok = isinstance(days, list) and bool(days) and all(isinstance(day, str) and day.lower() in DAYS for day in days)
    times_ok = isinstance(times, list) and bool(times) and all(isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) for value in times)
    limits_ok = all(type(schedule.get(name)) is int and schedule[name] > 0 for name in ("max_posts_per_account_per_day", "max_new_jobs_per_run"))
    check("schedule", days_ok and times_ok and limits_ok, "Days, local HH:MM times, and positive batch/daily limits are required.",
          "Choose the cadence and daily limits, then display the next three concrete local posting times.")
    authorization = object_value(profile.get("authorization"))
    mode = authorization.get("mode")
    scope = authorization.get("scope")
    permission_ok = mode == "review" or (mode == "automatic" and bool(scope) and bool(authorization.get("recorded_at")))
    check("authorization_record", permission_ok, "Review mode can prepare drafts; automatic mode needs a recorded scope. Neither is proof of current consent.",
          "Prepare a sample and ask for review mode or approval of a concrete automatic-posting scope; reuse existing valid consent.")
    agent_checks = [
        {"id": "live_connections", "status": "not_checked", "action": "Verify each selected account and its publishing permissions through a read-only connector call."},
        {"id": "media_upload_path", "status": "not_checked", "action": "Verify that the selected publisher supports local uploads, or separately approve and verify a media host providing a stable URL for the prepared asset."},
        {"id": "photo_editor", "status": "not_checked", "action": "Discover the host's image editor if photos need cleanup; offer originals if none is available."},
        {"id": "sample_and_consent", "status": "not_checked", "action": "Show the actual media, captions, accounts, and times; obtain only the authorization still missing."},
        {"id": "scheduler", "status": "not_checked", "action": "Inspect the actual scheduler and saved task ID, verify folder access and recurrence, and activate only within the agreed scope."},
    ]
    return {"workspace": str(workspace), "local_status": "needs_attention" if any(item["status"] == "needs_attention" for item in checks) else "local_checks_passed",
            "posting_readiness": "not_verified", "paused": profile.get("paused") if type(profile.get("paused")) is bool else None,
            "authorization_mode": mode if isinstance(mode, str) and mode in {"review", "automatic"} else None,
            "local_checks": checks, "connections": summaries, "agent_checks": agent_checks,
            "next_steps": steps + [{"id": item["id"], "action": item["action"]} for item in agent_checks],
            "note": "Read-only local report. No live service, image editor, authorization, or active schedule was verified."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize_parser = commands.add_parser("init", help="create a paused private workspace or resume existing settings")
    initialize_parser.add_argument("--workspace", required=True)
    initialize_parser.add_argument("--source", required=True)
    initialize_parser.add_argument("--recursive", action="store_true")
    doctor_parser = commands.add_parser("doctor", help="check local setup without writing or contacting services")
    doctor_parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    try:
        result = initialize(args.workspace, args.source, args.recursive) if args.command == "init" else doctor(args.workspace)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
