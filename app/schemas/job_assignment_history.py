"""Request/response DTOs for the job_assignment_history resource (read-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date
from typing import Any

from app.errors import APIError
from app.models import JobAssignmentHistory
from app.schemas.attendance import (
    ATTENDANCE_API_WORKDAY_LABELS,
    resolve_attendance_workday,
    verify_attendance_workday,
)
from app.utils import validate_employee_number

JOB_ASSIGNMENT_HISTORY_API_WORKDAY_LABELS = ATTENDANCE_API_WORKDAY_LABELS


# ---------------------------------------------------------------------
# Job assignment history — list query
# ---------------------------------------------------------------------
@dataclass
class ListJobAssignmentHistoryQuery:
    """Optional filters on ``GET /api/job-assignment-history``."""

    employee_number: str | None
    company_name: str | None
    workday: str | None
    """Response label when ``?workday=`` was set (``today`` or weekday name)."""
    ended_camp_date: date | None
    """Camp calendar date filter derived from ``workday`` (assignment end day)."""

    @classmethod
    def from_query(cls, args: Any) -> ListJobAssignmentHistoryQuery:
        employee_number: str | None = None
        raw_employee = args.get("employee_number")
        if raw_employee is not None and str(raw_employee).strip():
            slug = str(raw_employee).strip()
            valid, err = validate_employee_number(slug)
            if not valid:
                raise APIError(err, 400)
            employee_number = slug

        company_name: str | None = None
        raw_company = args.get("company_name")
        if raw_company is not None and str(raw_company).strip():
            company_name = str(raw_company).strip()

        workday: str | None = None
        ended_camp_date: date | None = None
        raw_workday = args.get("workday")
        if raw_workday is not None and str(raw_workday).strip():
            ctx = resolve_attendance_workday(str(raw_workday).strip())
            workday = ctx.workday
            ended_camp_date = ctx.camp_date

        return cls(
            employee_number=employee_number,
            company_name=company_name,
            workday=workday,
            ended_camp_date=ended_camp_date,
        )


@dataclass
class JobAssignmentHistoryWorkdayQuery:
    """Optional ``?workday=`` on per-person employment history."""

    workday: str | None

    @classmethod
    def from_query(cls, args: Any) -> JobAssignmentHistoryWorkdayQuery:
        raw = args.get("workday")
        if raw is None:
            return cls(workday=None)
        slug = str(raw).strip().lower()
        valid, err = verify_attendance_workday(slug)
        if not valid:
            raise APIError(err or "INVALID_ATTENDANCE_WORKDAY", 400)
        return cls(workday=slug)


# ---------------------------------------------------------------------
# Job assignment history — row / list responses
# ---------------------------------------------------------------------
@dataclass
class JobAssignmentHistoryRowResponse:
    employee_number: str
    first_name: str
    last_name: str
    age: int
    company_name: str
    hourly_pay: int
    tax: int
    started_at: str
    started_camp_date: str
    ended_at: str
    ended_camp_date: str
    minutes_worked: int
    end_reason: str
    created_at: str

    @classmethod
    def from_orm(cls, row: JobAssignmentHistory) -> JobAssignmentHistoryRowResponse:
        return cls(
            employee_number=row.employee_number,
            first_name=row.first_name,
            last_name=row.last_name,
            age=row.age,
            company_name=row.company_name,
            hourly_pay=row.hourly_pay,
            tax=row.tax,
            started_at=row.started_at.isoformat(),
            started_camp_date=row.started_camp_date.isoformat(),
            ended_at=row.ended_at.isoformat(),
            ended_camp_date=row.ended_camp_date.isoformat(),
            minutes_worked=row.minutes_worked,
            end_reason=row.end_reason,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )

    def to_dict(self) -> dict:
        return asdict(self)


JOB_ASSIGNMENT_HISTORY_CSV_COLUMNS = tuple(
    f.name for f in fields(JobAssignmentHistoryRowResponse)
)


@dataclass
class ListJobAssignmentHistoryResponse:
    history: list[JobAssignmentHistoryRowResponse]
    count: int
    workday: str | None = None
    ended_camp_date: str | None = None

    def to_dict(self) -> dict:
        result = {
            "history": [row.to_dict() for row in self.history],
            "count": self.count,
        }
        if self.workday is not None:
            result["workday"] = self.workday
        if self.ended_camp_date is not None:
            result["ended_camp_date"] = self.ended_camp_date
        return result


@dataclass
class ListJobAssignmentHistoryByEmployeeResponse:
    employee_number: str
    history: list[JobAssignmentHistoryRowResponse]
    count: int
    workday: str | None = None
    ended_camp_date: str | None = None

    def to_dict(self) -> dict:
        result = {
            "employee_number": self.employee_number,
            "history": [row.to_dict() for row in self.history],
            "count": self.count,
        }
        if self.workday is not None:
            result["workday"] = self.workday
        if self.ended_camp_date is not None:
            result["ended_camp_date"] = self.ended_camp_date
        return result
