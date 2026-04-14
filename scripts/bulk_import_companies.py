#!/usr/bin/env python3
"""Bulk import companies from CSV. Run with: python ./scripts/bulk_import_companies.py <path_to_csv>"""

import csv
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.database import db  # noqa: E402
from app.models import Company  # noqa: E402

load_dotenv(project_root / ".env")

REQUIRED_COLUMNS = ("company_name", "jobs_max", "pay_per_hour", "active", "notes")


def _parse_active(value: str) -> bool:
    """Parse active field from CSV (true/false, 1/0, yes/no)."""
    if value is None or value == "":
        return True
    return str(value).strip().lower() in ("true", "1", "yes")


def import_row(row: dict, row_num: int) -> bool:
    """Create or update a company from a CSV row. Returns True on success. Must be called within app context."""
    company_name = (row.get("company_name") or "").strip()
    jobs_max = (row.get("jobs_max") or "").strip()
    pay_per_hour = (row.get("pay_per_hour") or "").strip()
    active = _parse_active(row.get("active", "true"))
    notes = (row.get("notes") or "").strip() or None

    existing = Company.query.filter_by(company_name=company_name).first()
    if existing:
        existing.company_name = company_name
        existing.jobs_max = jobs_max
        existing.pay_per_hour = pay_per_hour
        existing.active = active
        existing.notes = notes
        db.session.commit()
        print(f"  Database entry UPDATED by CSV file row {row_num} - {company_name}")
    else:
        comp = Company(
            company_name=company_name,
            jobs_max=jobs_max,
            pay_per_hour=pay_per_hour,
            active=active,
            notes=notes,
        )
        db.session.add(comp)
        db.session.commit()
        print(f"  Database entry CREATED by CSV file row {row_num} - {company_name}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python ./scripts/bulk_import_companies.py <path_to_csv>",
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
