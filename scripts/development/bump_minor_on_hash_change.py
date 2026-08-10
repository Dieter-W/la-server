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
    file_changed_between_refs,
    format_version,
    is_checked_out_head,
    read_version_from_revision,
    resolve_remote_baseline,
    write_version_to_pyproject,
)


def git_commit(message: str) -> None:
    try:
        subprocess.run(
            ["git", "commit", "--no-verify", "-m", message, "--", PYPROJECT_PATH],
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

    if not is_checked_out_head(to_ref):
        print(
            f"Cannot auto-bump minor version when pushing {to_ref!r} "
            f"(checked-out branch is not the push target); "
            f"bump {PYPROJECT_PATH} manually and push again",
            file=sys.stderr,
        )
        return 1

    baseline_ref = resolve_remote_baseline(from_ref)
    if baseline_ref is None:
        print(
            f"Could not resolve remote baseline for {PYPROJECT_PATH}; "
            f"skipping minor bump"
        )
        return 0

    if not file_changed_between_refs(COMPATIBILITY_HASHES_PATH, baseline_ref, to_ref):
        print(
            f"{COMPATIBILITY_HASHES_PATH} unchanged since {baseline_ref}; no minor bump"
        )
        return 0

    remote_version = read_version_from_revision(baseline_ref)
    if remote_version is None:
        print(f"Could not read remote {PYPROJECT_PATH}; skipping minor bump")
        return 0

    current_version = read_version_from_revision(to_ref)
    if current_version is None:
        print(f"Could not read current {PYPROJECT_PATH}; skipping minor bump")
        return 0

    required_version = bump_minor(remote_version)
    if current_version >= required_version:
        print(
            f"Current version {format_version(current_version)} satisfies required "
            f"{format_version(required_version)} after hash change"
        )
        return 0

    write_version_to_pyproject(required_version)
    git_commit(
        f"chore: bump minor version to {format_version(required_version)} "
        f"(compatibility_hashes.json changed)"
    )
    print(
        f"Bumped minor version to {format_version(required_version)}; "
        f"push aborted — run git push again"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
