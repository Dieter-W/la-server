"""Bulk import part-time schedules and update them"""

import sys
import subprocess
from pathlib import Path

from app.models import PartTime

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EMPLOYEES_CSV = "./data/csv-example/employees_sample.csv"
_PART_TIME_CSV = "./data/csv-example/part_time_sample.csv"


def _run_bulk_import(script: str, csv_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, script, csv_path],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )


def _seed_employees() -> None:
    result = _run_bulk_import(
        "./scripts/bulk_import_employees.py",
        _EMPLOYEES_CSV,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------
# Part-time bulk import
# ---------------------------------------------------------------------
def test_bulk_import_part_time_create_ok(app, db_session):
    _seed_employees()

    result = _run_bulk_import(
        "./scripts/bulk_import_part_time.py",
        _PART_TIME_CSV,
    )
    assert result.returncode == 0, result.stderr

    data = PartTime.query.all()
    assert len(data) == 4


# ---------------------------------------------------------------------
# Part-time bulk update
# ---------------------------------------------------------------------
def test_bulk_import_part_time_update_ok(app, db_session):
    _seed_employees()

    result = _run_bulk_import(
        "./scripts/bulk_import_part_time.py",
        _PART_TIME_CSV,
    )
    assert result.returncode == 0, result.stderr

    data = PartTime.query.all()
    assert len(data) == 4

    result = _run_bulk_import(
        "./scripts/bulk_import_part_time.py",
        _PART_TIME_CSV,
    )
    assert result.returncode == 0, result.stderr

    data = PartTime.query.all()
    assert len(data) == 4


# ---------------------------------------------------------------------
# Part-time name mismatch rejection
# ---------------------------------------------------------------------
def test_bulk_import_part_time_name_mismatch(app, db_session, tmp_path):
    _seed_employees()

    bad_csv = tmp_path / "part_time_bad_name.csv"
    bad_csv.write_text(
        "first_name,last_name,employee_number,workday,shift,notes\n"
        "Wrong,Mustermann,M00155,monday,morning,\n",
        encoding="utf-8",
    )

    result = _run_bulk_import(
        "./scripts/bulk_import_part_time.py",
        str(bad_csv),
    )
    assert result.returncode == 1

    data = PartTime.query.all()
    assert len(data) == 0
