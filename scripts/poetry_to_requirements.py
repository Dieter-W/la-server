"""Rewrite the requirements.txt file when pyproject.toml has changed"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def get_staged_files():
    # Extract staged file names
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )

    except subprocess.CalledProcessError as e:
        print("Error checking git diff: ", e)
        sys.exit(1)

    return set(result.stdout.splitlines())


def main() -> int:
    # Check if pyproject.toml or poetry.look in the staged file set
    files = get_staged_files()
    changed_toml = "pyproject.toml" in files
    changed_lock = "poetry.lock" in files

    # Exit if none of the files is staged
    if not changed_toml and not changed_lock:
        print("pyproject.toml and poetry.lock not staged")
        sys.exit(0)

    # Exit if only one file is staged
    if changed_toml and not changed_lock:
        print("pyproject.toml is staged but not poetry.lock")
        sys.exit(1)
    if changed_lock and not changed_toml:
        print("poetry.lock is staged but not pyproject.toml")
        sys.exit(1)

    print("pyproject.toml changed, updating requirements.txt ...")

    # Move the new requirements.txt to ./data, we need it only for the production setup
    try:
        subprocess.run(
            [
                "poetry",
                "export",
                "-f", "requirements.txt",         # fmt: skip
                "--without-hashes",
                "-o", "./data/requirements.txt",  # fmt: skip
            ],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("Error exporting requirements.txt: ", e)
        sys.exit(1)

    # Add file to the commit
    try:
        subprocess.run(["git", "add", "./data/requirements.txt"], check=True)
    except subprocess.CalledProcessError as e:
        print("Error adding requirements.txt to the commit: ", e)
        sys.exit(1)

    print("requirements.txt updated and staged successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
