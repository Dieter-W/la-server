"""Bulk import company job-capacity schedules and update them"""

import sys
import subprocess
from pathlib import Path

from app.models import CompanyJobsMax

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPANIES_CSV = "./data/csv-example/companies_sample.csv"
_COMPANY_JOBS_MAX_CSV = "./data/csv-example/company_jobs_max_sample.csv"


def _run_bulk_import(script: str, csv_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, script, csv_path],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )


def _seed_companies() -> None:
    result = _run_bulk_import(
        "./scripts/bulk_import_companies.py",
        _COMPANIES_CSV,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------
# Company jobs max bulk import
# ---------------------------------------------------------------------
def test_bulk_import_company_jobs_max_create_ok(app, db_session):
    _seed_companies()

    result = _run_bulk_import(
        "./scripts/bulk_import_company_jobs_max.py",
        _COMPANY_JOBS_MAX_CSV,
    )
    assert result.returncode == 0, result.stderr

    data = CompanyJobsMax.query.all()
    assert len(data) == 4


# ---------------------------------------------------------------------
# Company jobs max bulk update
# ---------------------------------------------------------------------
def test_bulk_import_company_jobs_max_update_ok(app, db_session):
    _seed_companies()

    result = _run_bulk_import(
        "./scripts/bulk_import_company_jobs_max.py",
        _COMPANY_JOBS_MAX_CSV,
    )
    assert result.returncode == 0, result.stderr

    data = CompanyJobsMax.query.all()
    assert len(data) == 4

    result = _run_bulk_import(
        "./scripts/bulk_import_company_jobs_max.py",
        _COMPANY_JOBS_MAX_CSV,
    )
    assert result.returncode == 0, result.stderr

    data = CompanyJobsMax.query.all()
    assert len(data) == 4
