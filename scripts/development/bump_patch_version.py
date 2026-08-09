"""Pre-commit hook: bump patch version on every commit unless manually increased."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.development.version_bump import (
    PYPROJECT_PATH,
    bump_patch,
    compare_versions,
    git_show,
    read_version_from_toml,
    write_version_to_pyproject,
)


def merge_in_progress() -> bool:
    git_dir = project_root / ".git"
    return (git_dir / "MERGE_HEAD").is_file()


def get_staged_files() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error checking staged files: {exc}", file=sys.stderr)
        sys.exit(1)
    return set(result.stdout.splitlines())


def stage_pyproject() -> None:
    try:
        subprocess.run(
            ["git", "add", PYPROJECT_PATH],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error staging {PYPROJECT_PATH}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    if not get_staged_files():
        print("No staged files; skipping patch bump")
        return 0

    if merge_in_progress():
        print("Merge in progress; skipping patch bump")
        return 0

    head_toml = git_show("HEAD", PYPROJECT_PATH)
    if head_toml is None:
        print("No HEAD pyproject.toml; skipping patch bump")
        return 0

    head_version = read_version_from_toml(head_toml)
    staged_toml = git_show("", PYPROJECT_PATH)
    new_version = bump_patch(head_version)

    if staged_toml is not None:
        staged_version = read_version_from_toml(staged_toml)
        if compare_versions(staged_version, head_version) > 0:
            print(
                "Manual version increase detected in staged pyproject.toml; "
                "respecting staged version"
            )
            return 0
        if compare_versions(staged_version, new_version) == 0:
            print(f"Patch version already at {new_version}")
            return 0
    else:
        worktree_toml = (project_root / PYPROJECT_PATH).read_text(encoding="utf-8")
        worktree_version = read_version_from_toml(worktree_toml)
        if compare_versions(worktree_version, new_version) == 0:
            print(f"Patch version already at {new_version}")
            return 0

    write_version_to_pyproject(new_version)
    stage_pyproject()
    print(f"Bumped patch version to {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
