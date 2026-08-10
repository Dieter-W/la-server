"""Pre-commit hook: auto-update app/compatibility_hashes.json when needed."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.development.update_compatibility_hashes import (
    compute_hashes,
    load_file_hashes,
    write_hashes,
)
from scripts.development.version_bump import (
    COMPATIBILITY_HASHES_PATH,
    git_add,
)


def main() -> int:
    computed = compute_hashes()
    if computed == load_file_hashes():
        print(f"{COMPATIBILITY_HASHES_PATH} is up to date")
        return 0
    write_hashes(computed)
    git_add(COMPATIBILITY_HASHES_PATH)
    print(f"Updated and staged {COMPATIBILITY_HASHES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
