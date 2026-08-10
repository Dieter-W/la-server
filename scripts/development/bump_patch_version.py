"""Pre-commit hook: bump patch version on every commit unless manually increased."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.development.version_bump import (
    PYPROJECT_PATH,
    bump_patch,
    format_version,
    get_staged_files,
    git_add,
    git_show,
    read_version_from_toml,
    write_version_to_pyproject,
)


def merge_in_progress() -> bool:
    git_dir = project_root / ".git"
    return (git_dir / "MERGE_HEAD").is_file()


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
        if staged_version > head_version:
            print(
                "Manual version increase detected in staged pyproject.toml; "
                "respecting staged version"
            )
            return 0
        if staged_version == new_version:
            print(f"Patch version already at {format_version(new_version)}")
            return 0
    else:
        worktree_toml = (project_root / PYPROJECT_PATH).read_text(encoding="utf-8")
        worktree_version = read_version_from_toml(worktree_toml)
        if worktree_version == new_version:
            print(f"Patch version already at {format_version(new_version)}")
            return 0

    write_version_to_pyproject(new_version)
    git_add(PYPROJECT_PATH)
    print(f"Bumped patch version to {format_version(new_version)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
