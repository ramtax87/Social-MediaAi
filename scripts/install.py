#!/usr/bin/env python3
"""Install or update Social-MediaAi, preserving replaced installations in a backup."""
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid


NAME = "social-media-ai"


def manifest(root):
    """Compare actual file contents, ignoring disposable Python caches."""
    result = {}
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = sorted(name for name in folders if name not in {"__pycache__", ".git"})
        for name in folders + files:
            if (Path(directory) / name).is_symlink():
                raise ValueError(f"Symlink inside skill: {Path(directory) / name}. Review it before installing.")
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo")):
                continue
            path = Path(directory) / name
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            result[str(path.relative_to(root))] = digest.hexdigest()
    return result


def install(source, parent, update=False, check=False):
    source = Path(source).resolve()
    parent = Path(parent).expanduser().resolve()
    destination = parent / NAME
    if destination.is_symlink():
        raise ValueError(f"{destination} is a symlink. Update its linked source or choose another --destination; it was not replaced.")
    if source == destination or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("Source and destination must be separate directories; cannot install into the source checkout.")
    if not (source / "SKILL.md").is_file():
        raise ValueError(f"Bundled skill is missing SKILL.md: {source}")
    bundled = manifest(source)
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"Destination is not a directory: {destination}")
    state = "missing" if not destination.exists() else (
        "current" if manifest(destination) == bundled else "different")
    if check:
        return {"status": state, "destination": str(destination)}
    if state == "current":
        return {"status": "already installed", "destination": str(destination)}
    if state == "different" and not update:
        raise ValueError(f"Existing installation differs: {destination}. Run with --update to replace it while retaining a backup.")

    # Stage outside the skills directory so partial copies are never discovered.
    parent.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    with tempfile.TemporaryDirectory(prefix=".social-media-ai-install-", dir=parent.parent) as temporary:
        staged = Path(temporary) / NAME
        shutil.copytree(source, staged,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"))
        if manifest(staged) != bundled:
            raise ValueError("Bundled files changed during installation. Retry after the checkout is stable.")
        parent.mkdir(parents=True, exist_ok=True)
        if state == "different":
            backups = parent.parent / "skill-backups"
            backups.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = backups / f"{NAME}-{stamp}-{uuid.uuid4().hex[:8]}"
            destination.rename(backup)
        try:
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f"Destination appeared during installation: {destination}")
            staged.rename(destination)
        except OSError as exc:
            if backup:
                if not destination.exists() and not destination.is_symlink():
                    try:
                        backup.rename(destination)
                    except OSError as rollback:
                        raise OSError(f"Update failed; original preserved at {backup}. Restore failed: {rollback}") from exc
                else:
                    raise OSError(f"Update stopped; original preserved at {backup}; destination changed concurrently.") from exc
            raise
    result = {"status": "updated" if backup else "installed", "destination": str(destination)}
    if backup:
        result["backup"] = str(backup)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"
    parser.add_argument("--destination", type=Path, default=default,
                        help="Parent skills directory (default: $CODEX_HOME/skills or ~/.codex/skills)")
    parser.add_argument("--update", action="store_true", help="Replace an older installation and retain a backup")
    parser.add_argument("--check", action="store_true", help="Report installation status without changing files")
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1] / "skills" / NAME
    try:
        result = install(source, args.destination, args.update, args.check)
    except (OSError, ValueError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    print(f"{result['status'].capitalize()}: {result['destination']}")
    if result.get("backup"):
        print(f"Previous installation preserved: {result['backup']}")
    if args.check:
        return 0
    print("Use $social-media-ai in your agent. Reload skills or restart if it does not appear.")
    print("No accounts were connected and no posting schedule was activated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
