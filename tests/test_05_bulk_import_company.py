"""Bulk insert companies and update them"""

import sys
import subprocess

from app.models import Company


# ---------------------------------------------------------------------
# Companies bulk import
# ---------------------------------------------------------------------
def test_bulk_import_companies_create(app, db_session):
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_companies.py",
            "./data/csv-example/companies_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    data = Company.query.all()
    assert len(data) == 4


# ---------------------------------------------------------------------
# Companies bulk update
# ---------------------------------------------------------------------
def test_bulk_import_companies_update(app, db_session):
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_companies.py",
            "./data/csv-example/companies_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    data = Company.query.all()
    assert len(data) == 4

    # In place update, we use the same data
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_companies.py",
            "./data/csv-example/companies_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    data = Company.query.all()
    assert len(data) == 4
