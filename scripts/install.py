#!/usr/bin/env python3
"""Copy the bundled skill to a local skills directory without overwriting."""
import argparse
import os
from pathlib import Path
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"
    parser.add_argument("--destination", type=Path, default=default,
                        help="Parent skills directory (default: $CODEX_HOME/skills or ~/.codex/skills)")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills" / "social-media-ai"
    destination = args.destination.expanduser().resolve() / "social-media-ai"
    if destination.exists() or destination.is_symlink():
        parser.error(f"Already exists: {destination}. Review or remove it yourself before replacing it.")
    try:
        shutil.copytree(source, destination,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    except OSError as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Installed: {destination}")
    print("Use $social-media-ai in your agent. Reload skills or restart if it does not appear.")
    print("No accounts were connected and no posting schedule was activated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
