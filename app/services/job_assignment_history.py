"""Business logic for job assignment history (read-only audit trail)."""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.job_assignment_history import JobAssignmentHistoryRepository
from app.schemas.attendance import resolve_attendance_workday
from app.schemas.job_assignment_history import (
    JOB_ASSIGNMENT_HISTORY_CSV_COLUMNS,
    JobAssignmentHistoryRowResponse,
    JobAssignmentHistoryWorkdayQuery,
    ListJobAssignmentHistoryByEmployeeResponse,
    ListJobAssignmentHistoryQuery,
    ListJobAssignmentHistoryResponse,
)

CSV_BOM = "\ufeff"

CSV_COLUMNS = JOB_ASSIGNMENT_HISTORY_CSV_COLUMNS

# OWASP CSV/Excel formula injection: neutralize cells that start with formula triggers.
_CSV_FORMULA_PREFIXES = frozenset("=+-@\t\r")

# Content-Disposition filenames: allow only safe characters (independent of checksum validation).
_SAFE_FILENAME_PART_RE = re.compile(r"[^A-Za-z0-9_-]")


def _sanitize_csv_cell(value: object) -> object:
    if isinstance(value, str) and value and value[0] in _CSV_FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _sanitize_csv_row(row: dict[str, object]) -> dict[str, object]:
    return {key: _sanitize_csv_cell(value) for key, value in row.items()}


def _sanitize_csv_filename_part(value: str) -> str:
    """Strip characters unsafe for Content-Disposition attachment filenames."""
    return _SAFE_FILENAME_PART_RE.sub("", value)


class JobAssignmentHistoryService:
    def __init__(self, db: Session) -> None:
        self.repo = JobAssignmentHistoryRepository(db)

    # ---------------------------------------------------------------------
    # Lists (JSON)
    # ---------------------------------------------------------------------
    def list_history(
        self, query: ListJobAssignmentHistoryQuery
    ) -> ListJobAssignmentHistoryResponse:
        """All history rows with optional filters; newest ``ended_at`` first."""
        rows = self.repo.list_all(
            employee_number=query.employee_number,
            company_name=query.company_name,
            ended_camp_date=query.ended_camp_date,
        )
        history = [JobAssignmentHistoryRowResponse.from_orm(row) for row in rows]
        return ListJobAssignmentHistoryResponse(
            history=history,
            count=len(history),
            workday=query.workday,
            ended_camp_date=(
                query.ended_camp_date.isoformat()
                if query.ended_camp_date is not None
                else None
            ),
        )

    def list_history_by_employee(
        self,
        employee_number: str,
        query: JobAssignmentHistoryWorkdayQuery,
    ) -> ListJobAssignmentHistoryByEmployeeResponse:
        """Full employment history for one participant; optional ``?workday=`` filter."""
        ended_camp_date: date | None = None
        workday: str | None = None
        if query.workday is not None:
            ctx = resolve_attendance_workday(query.workday)
            workday = ctx.workday
            ended_camp_date = ctx.camp_date

        if ended_camp_date is not None:
            rows = self.repo.list_all(
                employee_number=employee_number,
                ended_camp_date=ended_camp_date,
            )
        else:
            rows = self.repo.list_by_employee_number(employee_number)

        history = [JobAssignmentHistoryRowResponse.from_orm(row) for row in rows]
        return ListJobAssignmentHistoryByEmployeeResponse(
            employee_number=employee_number,
            history=history,
            count=len(history),
            workday=workday,
            ended_camp_date=(
                ended_camp_date.isoformat() if ended_camp_date is not None else None
            ),
        )

    # ---------------------------------------------------------------------
    # CSV export
    # ---------------------------------------------------------------------
    @staticmethod
    def build_csv(rows: list[JobAssignmentHistoryRowResponse]) -> bytes:
        """UTF-8 CSV with BOM for Excel; stable column order."""
        buffer = io.StringIO()
        buffer.write(CSV_BOM)
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(_sanitize_csv_row(row.to_dict()))
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def csv_filename_for_list(ended_camp_date: date | None) -> str:
        suffix = ended_camp_date.isoformat() if ended_camp_date else "all"
        safe_suffix = _sanitize_csv_filename_part(suffix)
        return f"job-assignment-history-{safe_suffix}.csv"

    @staticmethod
    def csv_filename_for_employee(employee_number: str) -> str:
        safe_number = _sanitize_csv_filename_part(employee_number)
        return f"job-assignment-history-{safe_number}.csv"

    def export_history_csv(
        self, query: ListJobAssignmentHistoryQuery
    ) -> tuple[bytes, str]:
        """Filtered history as UTF-8 CSV bytes and attachment filename."""
        response = self.list_history(query)
        return (
            self.build_csv(response.history),
            self.csv_filename_for_list(query.ended_camp_date),
        )

    def export_history_by_employee_csv(
        self,
        employee_number: str,
        query: JobAssignmentHistoryWorkdayQuery,
    ) -> tuple[bytes, str]:
        """One participant's history as UTF-8 CSV bytes and attachment filename."""
        response = self.list_history_by_employee(employee_number, query)
        return (
            self.build_csv(response.history),
            self.csv_filename_for_employee(employee_number),
        )
