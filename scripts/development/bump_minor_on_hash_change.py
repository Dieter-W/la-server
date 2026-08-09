"""Pre-push hook: bump minor version when compatibility_hashes.json changed vs remote."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.development.version_bump import (
    COMPATIBILITY_HASHES_PATH,
    PYPROJECT_PATH,
    bump_minor,
    compare_versions,
    file_changed_between_refs,
    read_version_from_revision,
    write_version_to_pyproject,
)


def git_commit(message: str) -> None:
    try:
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error creating version bump commit: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    from_ref = os.environ.get("PRE_COMMIT_FROM_REF", "")
    to_ref = os.environ.get("PRE_COMMIT_TO_REF", "HEAD")

    if not from_ref:
        print("PRE_COMMIT_FROM_REF not set; skipping minor bump check")
        return 0

    if not file_changed_between_refs(COMPATIBILITY_HASHES_PATH, from_ref, to_ref):
        print(f"{COMPATIBILITY_HASHES_PATH} unchanged since remote; no minor bump")
        return 0

    remote_version = read_version_from_revision(from_ref)
    if remote_version is None:
        print(f"Could not read remote {PYPROJECT_PATH}; skipping minor bump")
        return 0

    current_version = read_version_from_revision("HEAD")
    if current_version is None:
        print(f"Could not read current {PYPROJECT_PATH}; skipping minor bump")
        return 0

    required_version = bump_minor(remote_version)
    if compare_versions(current_version, required_version) >= 0:
        print(
            f"Current version {current_version} satisfies required "
            f"{required_version} after hash change"
        )
        return 0

    write_version_to_pyproject(required_version)
    try:
        subprocess.run(
            ["git", "add", PYPROJECT_PATH],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error staging {PYPROJECT_PATH}: {exc}", file=sys.stderr)
        sys.exit(1)
    git_commit(
        f"chore: bump minor version to {required_version.major}."
        f"{required_version.minor}.{required_version.patch} "
        f"(compatibility_hashes.json changed)"
    )
    print(
        f"Bumped minor version to {required_version}; push aborted — run git push again"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
