#!/usr/bin/env python3
"""Bulk import camp participants (employee rows) from CSV.

Checksum validation follows ``VALIDATE_CHECK_SUM`` in ``.env`` (see app config).
Run with: python ./scripts/bulk_import_employees.py <path_to_csv>
"""

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
from app.models import Authentication, Employee  # noqa: E402
from app.auth.utils import hash_password, verify_access_group  # noqa: E402

load_dotenv(project_root / ".env")

REQUIRED_COLUMNS = (
    "first_name",
    "last_name",
    "employee_number",
    "role",
    "active",
    "auth_group",
    "notes",
)


def _parse_active(value: str) -> bool:
    """Parse active field from CSV (true/false, 1/0, yes/no)."""
    if value is None or value == "":
        return True
    return str(value).strip().lower() in ("true", "1", "yes")


def _is_blank_csv_row(row: dict) -> bool:
    """True if every cell is empty (e.g. trailing newline row in spreadsheets)."""
    for v in row.values():
        if v is not None and str(v).strip():
            return False
    return True


def _parse_auth_group(raw_auth_group) -> tuple[str | None, str | None]:
    """Normalize CSV auth_group. Returns (value or None if unset, error message or None)."""
    group_string = (raw_auth_group or "").strip()
    if not group_string:
        return None, None
    auth_group = group_string.lower()
    ok, msg = verify_access_group(auth_group)
    if not ok:
        return None, f"{msg} {group_string!r} (allowed: employee, staff, admin)"
    return auth_group, None


def import_row(session, row: dict, row_num: int) -> bool:
    """Create or update an employee from a CSV row. Returns True on success. Must be called within app context."""
    employee_number = (row.get("employee_number") or "").strip()
    if not employee_number:
        if _is_blank_csv_row(row):
            return True
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
    auth_group, auth_err = _parse_auth_group(row.get("auth_group"))
    if auth_err:
        print(f"  Row {row_num}: SKIP - {auth_err}")
        return False

    existing = (
        session.query(Employee).filter_by(employee_number=employee_number).first()
    )
    if existing:
        emp = existing
        emp.first_name = first_name
        emp.last_name = last_name
        emp.role = role
        emp.active = active
        emp.notes = notes
        emp.authentication.auth_group = auth_group
        emp.authentication.password_must_change = True
        emp.authentication.password_hash = hash_password(last_name)
        action = "UPDATED"
    else:
        emp = Employee(
            first_name=first_name,
            last_name=last_name,
            employee_number=employee_number,
            role=role,
            active=active,
            notes=notes,
            authentication=Authentication(
                auth_group=auth_group,
                password_must_change=True,
                password_hash=hash_password(last_name),
            ),
        )
        session.add(emp)
        action = "CREATED"

    session.commit()
    # codeql[py/clear-text-logging-sensitive-data]
    print(f"  Row {row_num}: {action} - {employee_number}")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python ./scripts/bulk_import_employees.py <path_to_csv>",
            file=sys.stderr,
        )
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    employee_checksum_validation = Config._env_bool("VALIDATE_CHECK_SUM", default=True)

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

        if employee_checksum_validation:
            for i, row in enumerate(rows, start=2):  # row 1 is header
                employee_number = (row.get("employee_number") or "").strip()
                if not employee_number:
                    continue
                if not mod_97_10.is_valid(employee_number):
                    first_name = (row.get("first_name") or "").strip()
                    last_name = (row.get("last_name") or "").strip()
                    # codeql[py/clear-text-logging-sensitive-data]
                    print(
                        f"Error: Checksum of Employee Number is wrong - {first_name} {last_name} - {employee_number} ",
                        file=sys.stderr,
                    )
                    sys.exit(1)

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
