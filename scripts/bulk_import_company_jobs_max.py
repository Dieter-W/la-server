#!/usr/bin/env python3
"""Bulk import company job-capacity schedules from CSV.

Prerequisite: companies must exist (import companies first).
Run with: python ./scripts/bulk_import_company_jobs_max.py <path_to_csv>
"""

import csv
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.errors import APIError  # noqa: E402
from app.models import Company, CompanyJobsMax  # noqa: E402
from app.schemas.company_jobs_max import verify_jobs_max  # noqa: E402
from app.schemas.part_time import (  # noqa: E402
    PartTimeShift,
    validate_part_time_combination,
    verify_part_time_shift,
    verify_part_time_stored_workday,
)

load_dotenv(project_root / ".env")

REQUIRED_COLUMNS = ("company_name", "workday", "shift", "jobs_max", "notes")

_BOOL_LIKE = frozenset({"true", "false", "yes", "no"})


def _is_blank_company_jobs_max_row(row: dict) -> bool:
    """True when company_name, workday, and shift are all empty."""
    company_name = (row.get("company_name") or "").strip()
    workday = (row.get("workday") or "").strip()
    shift = (row.get("shift") or "").strip()
    return not company_name and not workday and not shift


def _parse_jobs_max(raw, row_num: int) -> int | None:
    """Parse jobs_max as a non-negative integer; reject bool-like strings."""
    s = (raw or "").strip()
    if not s:
        print(f"  Row {row_num}: SKIP - missing jobs_max")
        return None
    if s.lower() in _BOOL_LIKE:
        print(f"  Row {row_num}: SKIP - jobs_max must be an integer, got {raw!r}")
        return None
    try:
        n = int(s, 10)
    except ValueError:
        print(f"  Row {row_num}: SKIP - jobs_max must be an integer, got {raw!r}")
        return None
    try:
        return verify_jobs_max(n)
    except APIError:
        print(
            f"  Row {row_num}: SKIP - jobs_max must be a non-negative integer, got {n}"
        )
        return None


def import_row(session, row: dict, row_num: int) -> bool:
    """Create or update a company_jobs_max row from CSV. Returns True on success."""
    if _is_blank_company_jobs_max_row(row):
        return True

    company_name = (row.get("company_name") or "").strip()
    workday_raw = (row.get("workday") or "").strip()
    shift_raw = (row.get("shift") or "").strip()
    notes = (row.get("notes") or "").strip() or None

    if not company_name:
        print(f"  Row {row_num}: SKIP - missing company_name")
        return False
    if not workday_raw:
        print(f"  Row {row_num}: SKIP - missing workday")
        return False

    jobs_max = _parse_jobs_max(row.get("jobs_max"), row_num)
    if jobs_max is None:
        return False

    workday = workday_raw.lower()
    valid, err = verify_part_time_stored_workday(workday)
    if not valid:
        print(f"  Row {row_num}: SKIP - invalid workday {workday_raw!r}")
        return False

    shift = shift_raw.lower() if shift_raw else PartTimeShift.ALL_DAY.value
    valid, err = verify_part_time_shift(shift)
    if not valid:
        print(f"  Row {row_num}: SKIP - invalid shift {shift_raw!r}")
        return False

    valid, err = validate_part_time_combination(workday, shift)
    if not valid:
        print(
            f"  Row {row_num}: SKIP - invalid workday/shift combination "
            f"({workday!r}, {shift!r})"
        )
        return False

    company = session.query(Company).filter_by(company_name=company_name).first()
    if company is None:
        print(f"  Row {row_num}: SKIP - company not found for name {company_name!r}")
        return False

    existing = (
        session.query(CompanyJobsMax)
        .filter_by(company_id=company.id, workday=workday, shift=shift)
        .first()
    )
    if existing:
        existing.jobs_max = jobs_max
        existing.notes = notes
        session.commit()
        print(
            f"  Database entry UPDATED by CSV file row {row_num} - "
            f"{company_name} / {workday} / {shift}"
        )
    else:
        session.add(
            CompanyJobsMax(
                company_id=company.id,
                workday=workday,
                shift=shift,
                jobs_max=jobs_max,
                notes=notes,
            )
        )
        session.commit()
        print(
            f"  Database entry CREATED by CSV file row {row_num} - "
            f"{company_name} / {workday} / {shift}"
        )
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python ./scripts/bulk_import_company_jobs_max.py <path_to_csv>",
            file=sys.stderr,
        )
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    app = create_app(Config)
    failed = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: CSV has no header row", file=sys.stderr)
            sys.exit(1)
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing:
            print(f"Error: CSV missing columns: {missing}", file=sys.stderr)
            sys.exit(1)

        rows = list(reader)

    with app.app_context():
        session = app.SessionLocal()
        try:
            for i, row in enumerate(rows, start=2):  # row 1 is header
                try:
                    if not import_row(session, row, i):
                        failed += 1
                except Exception as e:
                    session.rollback()
                    print(f"  Row {i}: ERROR - {e}")
                    failed += 1
        finally:
            session.close()

    if failed:
        print(f"\n{failed} row(s) failed to import.", file=sys.stderr)
        sys.exit(1)
    print("\nAll rows imported successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
