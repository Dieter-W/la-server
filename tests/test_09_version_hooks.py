"""Unit tests for version bump hooks and shared version_bump helpers."""

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
    check_compatibility_hashes,
)
from scripts.development.version_bump import (
    COMPATIBILITY_HASHES_PATH,
    NULL_REF,
    PYPROJECT_PATH,
    Version,
    bump_minor,
    bump_patch,
    changed_compatibility_areas,
    file_changed_between_refs,
    format_minor_bump_commit_message,
    format_version,
    parse_version,
    read_version_from_toml,
    required_version_for_hash_change,
    resolve_remote_baseline,
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


def test_version_tuple_ordering() -> None:
    assert Version(1, 0, 0) < Version(1, 0, 1)
    assert Version(1, 1, 0) > Version(1, 0, 9)
    assert Version(2, 0, 0) == Version(2, 0, 0)


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


def test_bump_patch_skips_when_no_staged_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bump_patch_version, "get_staged_files", lambda: set())

    assert bump_patch_version.main() == 0


def test_bump_patch_skips_during_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bump_patch_version, "get_staged_files", lambda: {"README.md"})
    monkeypatch.setattr(bump_patch_version, "merge_in_progress", lambda: True)

    assert bump_patch_version.main() == 0


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
    monkeypatch.setattr(bump_patch_version, "git_add", lambda *_: None)

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
    monkeypatch.setattr(bump_patch_version, "git_add", lambda *_: None)

    assert bump_patch_version.main() == 0
    assert written == [Version(1, 0, 1)]


def test_bump_patch_skips_when_worktree_already_bumped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    written: list[Version] = []

    monkeypatch.setattr(bump_patch_version, "project_root", tmp_path)
    (tmp_path / PYPROJECT_PATH).write_text(
        '[project]\nversion = "1.0.1"\n', encoding="utf-8"
    )
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
    monkeypatch.setattr(bump_patch_version, "git_add", lambda *_: None)

    assert bump_patch_version.main() == 0
    assert written == []


def test_bump_patch_increments_from_worktree_when_pyproject_not_staged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    written: list[Version] = []

    monkeypatch.setattr(bump_patch_version, "project_root", tmp_path)
    (tmp_path / PYPROJECT_PATH).write_text(
        '[project]\nversion = "1.0.0"\n', encoding="utf-8"
    )
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
    monkeypatch.setattr(bump_patch_version, "git_add", lambda *_: None)

    assert bump_patch_version.main() == 0
    assert written == [Version(1, 0, 1)]


def test_bump_minor_skips_when_hashes_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "collect_hash_baseline_refs",
        lambda _from_ref: ["origin/main"],
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "required_version_for_hash_change",
        lambda _to_ref, _refs: None,
    )

    assert bump_minor_on_hash_change.main() == 0


def test_bump_minor_aborts_when_to_ref_is_not_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "refs/heads/feature")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "is_checked_out_head",
        lambda _revision: False,
    )

    assert bump_minor_on_hash_change.main() == 1


def test_bump_minor_accepts_head_commit_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", head_sha)
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "collect_hash_baseline_refs",
        lambda _from_ref: ["origin/main"],
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "required_version_for_hash_change",
        lambda _to_ref, _refs: None,
    )

    assert bump_minor_on_hash_change.main() == 0


def test_bump_minor_aborts_push_when_version_too_low(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "is_checked_out_head",
        lambda _revision: True,
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "collect_hash_baseline_refs",
        lambda _from_ref: ["origin/main"],
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "required_version_for_hash_change",
        lambda _to_ref, _refs: Version(1, 3, 0),
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "read_version_from_revision",
        lambda revision: Version(1, 2, 3) if revision == "HEAD" else None,
    )
    written: list[Version] = []
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "write_version_to_pyproject",
        lambda version: written.append(version),
    )
    monkeypatch.setattr(bump_minor_on_hash_change, "git_commit", lambda _message: None)

    assert bump_minor_on_hash_change.main() == 1
    assert written == [Version(1, 3, 0)]


def test_bump_minor_passes_when_version_already_sufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "is_checked_out_head",
        lambda _revision: True,
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "collect_hash_baseline_refs",
        lambda _from_ref: ["origin/main"],
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "required_version_for_hash_change",
        lambda _to_ref, _refs: Version(1, 3, 0),
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "read_version_from_revision",
        lambda revision: Version(1, 3, 0) if revision == "HEAD" else None,
    )

    assert bump_minor_on_hash_change.main() == 0


def test_bump_minor_when_remote_branch_already_has_hash_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/hotfix/companies")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "is_checked_out_head",
        lambda _revision: True,
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "collect_hash_baseline_refs",
        lambda _from_ref: ["origin/hotfix/companies", "origin/main"],
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "required_version_for_hash_change",
        lambda _to_ref, _refs: Version(1, 2, 0),
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "read_version_from_revision",
        lambda revision: Version(1, 1, 9) if revision == "HEAD" else None,
    )
    written: list[Version] = []
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "write_version_to_pyproject",
        lambda version: written.append(version),
    )
    monkeypatch.setattr(bump_minor_on_hash_change, "git_commit", lambda _message: None)

    assert bump_minor_on_hash_change.main() == 1
    assert written == [Version(1, 2, 0)]


def test_bump_minor_uses_main_baseline_on_new_branch_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", NULL_REF)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "is_checked_out_head",
        lambda _revision: True,
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "collect_hash_baseline_refs",
        lambda _from_ref: ["origin/main"],
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "required_version_for_hash_change",
        lambda _to_ref, _refs: Version(1, 2, 0),
    )
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "read_version_from_revision",
        lambda revision: Version(1, 1, 7) if revision == "HEAD" else None,
    )
    written: list[Version] = []
    monkeypatch.setattr(
        bump_minor_on_hash_change,
        "write_version_to_pyproject",
        lambda version: written.append(version),
    )
    monkeypatch.setattr(bump_minor_on_hash_change, "git_commit", lambda _message: None)

    assert bump_minor_on_hash_change.main() == 1
    assert written == [Version(1, 2, 0)]


def test_resolve_remote_baseline_prefers_valid_from_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.development.version_bump.revision_has_pyproject",
        lambda revision: revision == "origin/hotfix/companies",
    )

    assert (
        resolve_remote_baseline("origin/hotfix/companies") == "origin/hotfix/companies"
    )


def test_resolve_remote_baseline_falls_back_to_main_for_null_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.development.version_bump.revision_has_pyproject",
        lambda revision: revision == "origin/main",
    )

    assert resolve_remote_baseline(NULL_REF) == "origin/main"


def test_required_version_for_hash_change_uses_highest_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.development.version_bump.file_changed_between_refs",
        lambda _path, baseline, _to_ref: baseline == "origin/main",
    )
    monkeypatch.setattr(
        "scripts.development.version_bump.read_version_from_revision",
        lambda revision: Version(1, 1, 3) if revision == "origin/main" else None,
    )

    assert required_version_for_hash_change(
        "HEAD", ["origin/hotfix/companies", "origin/main"]
    ) == Version(1, 2, 0)


def test_changed_compatibility_areas_lists_api_and_schema_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.development.version_bump.load_hashes_from_revision",
        lambda revision: {
            "before": {
                "api_compatibility_hashes": {"companies": "old", "auth": "same"},
                "schema_compatibility_hashes": {"companies": "same"},
            },
            "after": {
                "api_compatibility_hashes": {"companies": "new", "auth": "same"},
                "schema_compatibility_hashes": {"companies": "new"},
            },
        }.get(revision),
    )

    assert changed_compatibility_areas("before", "after") == [
        "API companies",
        "schema companies",
    ]


def test_format_minor_bump_commit_message_includes_version_tag_and_areas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.development.version_bump.changed_compatibility_areas",
        lambda _baseline, _to_ref: ["API companies"],
    )

    message = format_minor_bump_commit_message(
        Version(1, 2, 0), "HEAD", ["origin/main"]
    )

    assert message == "v1.2.0: compatibility changed for API companies"


COMPUTED_HASHES = {
    "api_compatibility_hashes": {"auth": "abc123def4567890"},
    "schema_compatibility_hashes": {"companies": "fedcba0987654321"},
}
STALE_HASHES = {
    "api_compatibility_hashes": {"auth": "0000000000000000"},
    "schema_compatibility_hashes": {"companies": "1111111111111111"},
}


def test_compatibility_hashes_noop_when_up_to_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written: list[dict[str, dict[str, str]]] = []

    monkeypatch.setattr(
        check_compatibility_hashes, "compute_hashes", lambda: COMPUTED_HASHES
    )
    monkeypatch.setattr(
        check_compatibility_hashes, "load_file_hashes", lambda: COMPUTED_HASHES
    )
    monkeypatch.setattr(
        check_compatibility_hashes,
        "write_hashes",
        lambda payload: written.append(payload),
    )
    monkeypatch.setattr(check_compatibility_hashes, "git_add", lambda *_: None)

    assert check_compatibility_hashes.main() == 0
    assert written == []


def test_compatibility_hashes_updates_on_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written: list[dict[str, dict[str, str]]] = []
    staged_calls: list[bool] = []

    monkeypatch.setattr(
        check_compatibility_hashes, "compute_hashes", lambda: COMPUTED_HASHES
    )
    monkeypatch.setattr(
        check_compatibility_hashes, "load_file_hashes", lambda: STALE_HASHES
    )
    monkeypatch.setattr(
        check_compatibility_hashes,
        "write_hashes",
        lambda payload: written.append(payload),
    )
    monkeypatch.setattr(
        check_compatibility_hashes,
        "git_add",
        lambda *_: staged_calls.append(True),
    )

    assert check_compatibility_hashes.main() == 0
    assert written == [COMPUTED_HASHES]
    assert staged_calls == [True]
