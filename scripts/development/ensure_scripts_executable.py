"""Pre-commit hook: git executable bit on scripts/*.py, scripts/*.sh, and root *.sh."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

EXECUTABLE_RE = re.compile(r"^(?:scripts/[^/]+\.(?:py|sh)|[^/]+\.sh)$")
NON_EXECUTABLE_RE = re.compile(r"^scripts/development/.*\.py$")
EXECUTABLE_MODE = "100755"
NON_EXECUTABLE_MODE = "100644"


def git_ls_files() -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        mode, _, _, path = line.split(maxsplit=3)
        if EXECUTABLE_RE.match(path) or NON_EXECUTABLE_RE.match(path):
            entries.append((path, mode))
    return entries


def update_mode(path: str, executable: bool) -> None:
    flag = "+x" if executable else "-x"
    subprocess.run(
        ["git", "update-index", f"--chmod={flag}", path],
        cwd=project_root,
        check=True,
    )


def stage(path: str) -> None:
    subprocess.run(
        ["git", "add", "--", path],
        cwd=project_root,
        check=True,
    )


def main() -> int:
    changed: list[str] = []

    for path, mode in git_ls_files():
        if EXECUTABLE_RE.match(path) and mode != EXECUTABLE_MODE:
            update_mode(path, executable=True)
            changed.append(path)
        elif NON_EXECUTABLE_RE.match(path) and mode != NON_EXECUTABLE_MODE:
            update_mode(path, executable=False)
            changed.append(path)

    if not changed:
        print("Script executable bits are correct")
        return 0

    for path in changed:
        stage(path)

    print("Updated git executable bits:")
    for path in changed:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Error updating script executable bits: {exc}", file=sys.stderr)
        sys.exit(1)
