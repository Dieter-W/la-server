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
    collect_hash_baseline_refs,
    format_minor_bump_commit_message,
    format_version,
    is_checked_out_head,
    read_version_from_revision,
    required_version_for_hash_change,
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

    baseline_refs = collect_hash_baseline_refs(from_ref)
    if not baseline_refs:
        print(
            f"Could not resolve any baseline for {COMPATIBILITY_HASHES_PATH}; "
            f"skipping minor bump"
        )
        return 0

    required_version = required_version_for_hash_change(to_ref, baseline_refs)
    if required_version is None:
        print(
            f"{COMPATIBILITY_HASHES_PATH} unchanged since {', '.join(baseline_refs)}; "
            f"no minor bump"
        )
        return 0

    current_version = read_version_from_revision(to_ref)
    if current_version is None:
        print(f"Could not read current {PYPROJECT_PATH}; skipping minor bump")
        return 0

    if current_version >= required_version:
        print(
            f"Current version {format_version(current_version)} satisfies required "
            f"{format_version(required_version)} after hash change"
        )
        return 0

    write_version_to_pyproject(required_version)
    git_commit(
        format_minor_bump_commit_message(required_version, to_ref, baseline_refs)
    )
    print(
        f"Bumped minor version to {format_version(required_version)}; "
        f"push aborted — run git push again"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
