"""Unit tests for scripts/development/version_bump.py helpers and bump decision logic."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from scripts.development import (
    bump_minor_on_hash_change,
    bump_patch_version,
)
from scripts.development.version_bump import (
    COMPATIBILITY_HASHES_PATH,
    PYPROJECT_PATH,
    Version,
    bump_minor,
    bump_patch,
    compare_versions,
    file_changed_between_refs,
    format_version,
    parse_version,
    read_version_from_toml,
    write_version_in_toml,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.0.0", Version(1, 0, 0)),
        ("12.34.56", Version(12, 34, 56)),
    ],
)
def test_parse_version(value: str, expected: Version) -> None:
    assert parse_version(value) == expected


@pytest.mark.parametrize("value", ["1.0", "v1.0.0", "1.0.0-beta", ""])
def test_parse_version_rejects_invalid(value: str) -> None:
    with pytest.raises(ValueError):
        parse_version(value)


def test_format_version_round_trip() -> None:
    version = Version(2, 3, 4)
    assert parse_version(format_version(version)) == version


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (Version(1, 0, 0), Version(1, 0, 1), -1),
        (Version(1, 1, 0), Version(1, 0, 9), 1),
        (Version(2, 0, 0), Version(2, 0, 0), 0),
    ],
)
def test_compare_versions(left: Version, right: Version, expected: int) -> None:
    assert compare_versions(left, right) == expected


def test_bump_patch() -> None:
    assert bump_patch(Version(1, 2, 3)) == Version(1, 2, 4)


def test_bump_minor_resets_patch() -> None:
    assert bump_minor(Version(1, 2, 3)) == Version(1, 3, 0)


def test_read_and_write_version_in_toml() -> None:
    sample = '[project]\nname = "demo"\nversion = "1.2.3"\n'
    assert read_version_from_toml(sample) == Version(1, 2, 3)
    updated = write_version_in_toml(sample, Version(2, 0, 0))
    assert read_version_from_toml(updated) == Version(2, 0, 0)
    assert 'version = "2.0.0"' in updated


def test_file_changed_between_refs_detects_difference() -> None:
    with patch(
        "scripts.development.version_bump.git_show",
        side_effect=["old", "new"],
    ):
        assert file_changed_between_refs("path.json", "origin/main", "HEAD") is True


def test_file_changed_between_refs_unchanged() -> None:
    payload = '{"api": "same"}\n'
    with patch(
        "scripts.development.version_bump.git_show",
        side_effect=[payload, payload],
    ):
        assert (
            file_changed_between_refs(COMPATIBILITY_HASHES_PATH, "origin/main", "HEAD")
            is False
        )


def test_bump_patch_respects_manual_increase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bump_patch_version, "get_staged_files", lambda: {"README.md"})
    monkeypatch.setattr(bump_patch_version, "merge_in_progress", lambda: False)
    monkeypatch.setattr(
        bump_patch_version,
        "git_show",
        lambda revision, path: {
            ("HEAD", PYPROJECT_PATH): '[project]\nversion = "1.0.0"\n',
            ("", PYPROJECT_PATH): '[project]\nversion = "1.5.0"\n',
        }.get((revision, path)),
    )
    monkeypatch.setattr(
        bump_patch_version, "write_version_to_pyproject", lambda *_: None
    )
    monkeypatch.setattr(bump_patch_version, "stage_pyproject", lambda: None)

    assert bump_patch_version.main() == 0


def test_bump_patch_increments_when_not_manually_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written: list[Version] = []

    monkeypatch.setattr(bump_patch_version, "get_staged_files", lambda: {"README.md"})
    monkeypatch.setattr(bump_patch_version, "merge_in_progress", lambda: False)
    monkeypatch.setattr(
        bump_patch_version,
        "git_show",
        lambda revision, path: {
            ("HEAD", PYPROJECT_PATH): '[project]\nversion = "1.0.0"\n',
        }.get((revision, path)),
    )
    monkeypatch.setattr(
        bump_patch_version,
        "write_version_to_pyproject",
        lambda version: written.append(version),
    )
    monkeypatch.setattr(bump_patch_version, "stage_pyproject", lambda: None)

    assert bump_patch_version.main() == 0
    assert written == [Version(1, 0, 1)]


def test_bump_minor_skips_when_hashes_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "file_changed_between_refs",
        lambda *_args, **_kwargs: False,
    )

    assert bump_minor_on_hash_change.main() == 0


def test_bump_minor_aborts_push_when_version_too_low(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "file_changed_between_refs",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "read_version_from_revision",
        lambda revision: {
            "origin/main": Version(1, 2, 3),
            "HEAD": Version(1, 2, 3),
        }.get(revision),
    )
    written: list[Version] = []
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "write_version_to_pyproject",
        lambda version: written.append(version),
    )
    monkeypatch.setattr(bump_minor_on_hash_change, "git_commit", lambda _message: None)
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0)
    )

    assert bump_minor_on_hash_change.main() == 1
    assert written == [Version(1, 3, 0)]


def test_bump_minor_passes_when_version_already_sufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "file_changed_between_refs",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "read_version_from_revision",
        lambda revision: {
            "origin/main": Version(1, 2, 3),
            "HEAD": Version(1, 3, 0),
        }.get(revision),
    )

    assert bump_minor_on_hash_change.main() == 0
