"""Bulk insert employees and update them"""

import sys
import subprocess
from pathlib import Path

from app.models import Employee

_REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------
# Employees bulk import
# ---------------------------------------------------------------------
def test_bulk_import_employees_create(app, db_session):
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr

    data = Employee.query.all()
    assert len(data) == 4


# ---------------------------------------------------------------------
# Employees bulk update
# ---------------------------------------------------------------------
def test_bulk_import_employees_update(app, db_session):
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr

    data = Employee.query.all()
    assert len(data) == 4

    # In place update, we use the same data
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr

    data = Employee.query.all()
    assert len(data) == 4
