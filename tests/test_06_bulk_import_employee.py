"""Bulk insert employees and update them"""

import sys
import subprocess

from app.models import Employee


# ---------------------------------------------------------------------
# Employees bulk import
# ---------------------------------------------------------------------
def test_bulk_import_companies_create(app, db_session):
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    data = Employee.query.all()
    assert len(data) == 4


# ---------------------------------------------------------------------
# Employees bulk update
# ---------------------------------------------------------------------
def test_bulk_import_companies_update(app, db_session):
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

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
    )
    assert result.returncode == 0

    data = Employee.query.all()
    assert len(data) == 4
