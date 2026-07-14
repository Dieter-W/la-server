#!/usr/bin/env python3
"""Bulk import part-time schedules from CSV.

Prerequisite: employees must exist (import employees first).
Run with: python ./scripts/bulk_import_part_time.py <path_to_csv>
"""

import csv
import sys
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.models import Employee, PartTime  # noqa: E402
from app.schemas.part_time import (  # noqa: E402
    PartTimeShift,
    validate_part_time_combination,
    verify_part_time_shift,
    verify_part_time_stored_workday,
)

load_dotenv(project_root / ".env")

REQUIRED_COLUMNS = (
    "first_name",
    "last_name",
    "employee_number",
    "workday",
    "shift",
    "notes",
)


def _nfc(value: str) -> str:
    """Trim and NFC-normalize a name for comparison."""
    return unicodedata.normalize("NFC", value.strip())


def _is_blank_part_time_row(row: dict) -> bool:
    """True when employee_number, first_name, and last_name are all empty."""
    employee_number = (row.get("employee_number") or "").strip()
    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    return not employee_number and not first_name and not last_name


def import_row(session, row: dict, row_num: int) -> bool:
    """Create or update a part-time row from CSV. Returns True on success."""
    if _is_blank_part_time_row(row):
        return True

    employee_number = (row.get("employee_number") or "").strip()
    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    workday_raw = (row.get("workday") or "").strip()
    shift_raw = (row.get("shift") or "").strip()
    notes = (row.get("notes") or "").strip() or None

    if not employee_number:
        print(f"  Row {row_num}: SKIP - missing employee_number")
        return False
    if not first_name or not last_name:
        print(
            f"  Row {row_num}: SKIP - missing required field (first_name or last_name)"
        )
        return False
    if not workday_raw:
        print(f"  Row {row_num}: SKIP - missing workday")
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

    employee = (
        session.query(Employee).filter_by(employee_number=employee_number).first()
    )
    if employee is None:
        print(
            f"  Row {row_num}: SKIP - employee not found for number {employee_number!r}"
        )
        return False

    if _nfc(first_name) != _nfc(employee.first_name):
        print(
            f"  Row {row_num}: SKIP - first_name {first_name!r} does not match "
            f"employee {employee_number!r} ({employee.first_name!r})"
        )
        return False
    if _nfc(last_name) != _nfc(employee.last_name):
        print(
            f"  Row {row_num}: SKIP - last_name {last_name!r} does not match "
            f"employee {employee_number!r} ({employee.last_name!r})"
        )
        return False

    existing = (
        session.query(PartTime)
        .filter_by(employee_id=employee.id, workday=workday)
        .first()
    )
    if existing:
        existing.shift = shift
        existing.notes = notes
        session.commit()
        print(
            f"  Database entry UPDATED by CSV file row {row_num} - "
            f"{employee_number} / {workday}"
        )
    else:
        session.add(
            PartTime(
                employee_id=employee.id,
                workday=workday,
                shift=shift,
                notes=notes,
            )
        )
        session.commit()
        print(
            f"  Database entry CREATED by CSV file row {row_num} - "
            f"{employee_number} / {workday}"
        )
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python ./scripts/bulk_import_part_time.py <path_to_csv>",
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
