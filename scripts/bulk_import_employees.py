#!/usr/bin/env python3
"""Bulk import employees from CSV. Run with: python ./scripts/bulk_import_employees.py <path_to_csv> <--nochecksum-check>"""

import csv
import sys
from pathlib import Path

from dotenv import load_dotenv
from stdnum.iso7064 import mod_97_10

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.database import db  # noqa: E402
from app.models import Employee  # noqa: E402

load_dotenv(project_root / ".env")

REQUIRED_COLUMNS = (
    "first_name",
    "last_name",
    "employee_number",
    "role",
    "active",
    "notes",
)


def _parse_active(value: str) -> bool:
    """Parse active field from CSV (true/false, 1/0, yes/no)."""
    if value is None or value == "":
        return True
    return str(value).strip().lower() in ("true", "1", "yes")


def import_row(row: dict, row_num: int) -> bool:
    """Create or update an employee from a CSV row. Returns True on success. Must be called within app context."""
    employee_number = (row.get("employee_number") or "").strip()
    if not employee_number:
        print(f"  Row {row_num}: SKIP - missing employee_number")
        return False

    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    role = (row.get("role") or "").strip()
    if not first_name or not last_name or not role:
        print(
            f"  Row {row_num}: SKIP - missing required field (first_name, last_name, or role)"
        )
        return False

    active = _parse_active(row.get("active", "true"))
    notes = (row.get("notes") or "").strip() or None

    existing = Employee.query.filter_by(employee_number=employee_number).first()
    if existing:
        existing.first_name = first_name
        existing.last_name = last_name
        existing.role = role
        existing.active = active
        existing.notes = notes
        db.session.commit()
        print(f"  Row {row_num}: UPDATED - {employee_number}")
    else:
        emp = Employee(
            first_name=first_name,
            last_name=last_name,
            employee_number=employee_number,
            role=role,
            active=active,
            notes=notes,
        )
        db.session.add(emp)
        db.session.commit()
        print(f"  Row {row_num}: CREATED - {employee_number}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python ./scripts/bulk_import_employees.py <path_to_csv> <--no-checksum-check>",
            file=sys.stderr,
        )
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 3 or "--nochecksum-check" not in sys.argv[2].lower():
        employee_checksum_validation = True
    else:
        print(
            "Warning: Checksum validation of employee number is deactivated",
            file=sys.stderr,
        )
        employee_checksum_validation = False

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

        if employee_checksum_validation is not False:
            for i, row in enumerate(rows, start=2):  # row 1 is header
                if not mod_97_10.is_valid((row.get("employee_number") or "").strip()):
                    employee_number = (row.get("employee_number") or "").strip()
                    first_name = (row.get("first_name") or "").strip()
                    last_name = (row.get("last_name") or "").strip()
                    print(
                        f"Error: Checksum of Employee Number is wrong - {first_name} {last_name} - {employee_number} ",
                        file=sys.stderr,
                    )
                    sys.exit(1)

    with app.app_context():
        for i, row in enumerate(rows, start=2):  # row 1 is header
            try:
                if not import_row(row, i):
                    failed += 1
            except Exception as e:
                print(f"  Row {i}: ERROR - {e}")
                failed += 1

    if failed:
        print(f"\n{failed} row(s) failed to import.", file=sys.stderr)
        sys.exit(1)
    print("\nAll rows imported successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
