"""Rewrite the requirements.txt file when pyproject.toml has changed"""

import subprocess
import sys
import tomllib
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


def git_show(revision: str, path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "show", f"{revision}:{path}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None
    return result.stdout


def dependency_snapshot(toml_text: str) -> dict:
    data = tomllib.loads(toml_text)
    project = data.get("project", {})
    return {
        "requires-python": project.get("requires-python"),
        "dependencies": project.get("dependencies"),
        "dependency-groups": data.get("dependency-groups"),
    }


def poetry_dependencies_changed() -> bool:
    staged = git_show("", "pyproject.toml")
    if staged is None:
        return True
    head = git_show("HEAD", "pyproject.toml")
    if head is None:
        return True
    return dependency_snapshot(staged) != dependency_snapshot(head)


def export_requirements() -> int:
    print("pyproject.toml changed, updating requirements.txt ...")

    try:
        subprocess.run(
            [
                "poetry",
                "export",
                "-f",
                "requirements.txt",  # fmt: skip
                "--without-hashes",
                "-o",
                "./data/requirements.txt",  # fmt: skip
            ],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("Error exporting requirements.txt: ", e)
        return 1

    try:
        subprocess.run(["git", "add", "./data/requirements.txt"], check=True)
    except subprocess.CalledProcessError as e:
        print("Error adding requirements.txt to the commit: ", e)
        return 1

    print("requirements.txt updated and staged successfully")
    return 0


def main() -> int:
    files = get_staged_files()
    changed_toml = "pyproject.toml" in files
    changed_lock = "poetry.lock" in files

    if not changed_toml and not changed_lock:
        print("pyproject.toml and poetry.lock not staged")
        return 0

    if changed_toml and not changed_lock:
        if poetry_dependencies_changed():
            print("pyproject.toml is staged but not poetry.lock")
            return 1
        print("pyproject.toml changed without dependency updates; skipping export")
        return 0

    if changed_lock and not changed_toml:
        print("poetry.lock is staged but not pyproject.toml")
        return 1

    return export_requirements()


if __name__ == "__main__":
    sys.exit(main())
