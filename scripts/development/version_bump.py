"""Shared semver helpers and pyproject.toml read/write for version bump hooks."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import NamedTuple

project_root = Path(__file__).resolve().parent.parent.parent

VERSION_PATTERN = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)$",
)

PYPROJECT_PATH = "pyproject.toml"
COMPATIBILITY_HASHES_PATH = "app/compatibility_hashes.json"


class Version(NamedTuple):
    major: int
    minor: int
    patch: int


def parse_version(value: str) -> Version:
    match = VERSION_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"invalid semver: {value!r}")
    return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def format_version(version: Version) -> str:
    return f"{version.major}.{version.minor}.{version.patch}"


def compare_versions(left: Version, right: Version) -> int:
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def bump_patch(version: Version) -> Version:
    return Version(version.major, version.minor, version.patch + 1)


def bump_minor(version: Version) -> Version:
    return Version(version.major, version.minor + 1, 0)


def git_show(revision: str, path: str) -> str | None:
    spec = f":{path}" if revision == "" else f"{revision}:{path}"
    try:
        result = subprocess.run(
            ["git", "show", spec],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None
    return result.stdout


def read_version_from_toml(toml_text: str) -> Version:
    data = tomllib.loads(toml_text)
    version = data.get("project", {}).get("version")
    if not isinstance(version, str):
        raise TypeError("project.version missing or not a string in pyproject.toml")
    return parse_version(version)


def write_version_in_toml(toml_text: str, version: Version) -> str:
    formatted = format_version(version)
    pattern = re.compile(
        r'^(version\s*=\s*")([^"]+)(")',
        re.MULTILINE,
    )
    updated, count = pattern.subn(rf"\g<1>{formatted}\g<3>", toml_text, count=1)
    if count != 1:
        raise ValueError("could not locate project.version in pyproject.toml")
    return updated


def read_version_from_revision(revision: str) -> Version | None:
    toml_text = git_show(revision, PYPROJECT_PATH)
    if toml_text is None:
        return None
    return read_version_from_toml(toml_text)


def write_version_to_pyproject(version: Version, root: Path | None = None) -> None:
    root = root or project_root
    pyproject_path = root / PYPROJECT_PATH
    current = pyproject_path.read_text(encoding="utf-8")
    pyproject_path.write_text(
        write_version_in_toml(current, version),
        encoding="utf-8",
    )


def file_changed_between_refs(path: str, from_ref: str, to_ref: str) -> bool:
    before = git_show(from_ref, path)
    after = git_show(to_ref, path)
    return before != after
