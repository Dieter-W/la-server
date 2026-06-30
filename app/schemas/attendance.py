"""Request/response DTOs and camp-date helpers for attendance (check-in / check-out)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import app.camp_time as camp_time
from app.errors import APIError
from app.models import Attendance, Employee
from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    PART_TIME_CALENDAR_WORKDAYS,
    WEEKDAYS_WORKDAY,
    verify_part_time_workday,
)
from app.village_config import (
    require_attendance_for_kids,
    require_attendance_for_staff,
)

ATTENDANCE_API_WORKDAY_LABELS = ["today", *PART_TIME_CALENDAR_WORKDAYS]
_ATTENDANCE_REJECTED_WORKDAYS = frozenset({"all", WEEKDAYS_WORKDAY, ALL_WEEK_WORKDAY})

camp_today = camp_time.camp_today


def auth_group_for(emp: Employee) -> str:
    """Return JWT ``auth_group`` tier for a participant (``employee`` when no auth row)."""
    if emp.authentication is not None:
        return emp.authentication.auth_group
    return "employee"


def participant_requires_attendance(emp: Employee) -> bool:
    """True when job-assignment create/delete must gate on today's check-in row."""
    group = auth_group_for(emp)
    if group in ("staff", "admin"):
        return require_attendance_for_staff()
    return require_attendance_for_kids()


def verify_attendance_workday(workday: str) -> tuple[bool, str | None]:
    """Verify list/history ``workday`` query (``today`` or calendar weekday only)."""
    slug = workday.strip().lower()
    if slug == "today":
        return True, None
    if slug in _ATTENDANCE_REJECTED_WORKDAYS:
        return False, "INVALID_ATTENDANCE_WORKDAY"
    return verify_part_time_workday(slug)


@dataclass(frozen=True)
class AttendanceWorkdayContext:
    """Resolved ``?workday=`` query: API label and calendar ``camp_date``."""

    workday: str
    """Response ``workday`` value (``today`` or weekday name)."""
    camp_date: date
    """Calendar date in camp timezone for the resolved workday."""


def resolve_attendance_workday(
    param: str | None,
    *,
    now: datetime | None = None,
) -> AttendanceWorkdayContext:
    """Resolve ``?workday=`` for attendance list/history (default ``today``).

    ``monday`` … ``sunday`` map to that weekday in the ISO week containing camp today.
    Rejects aggregate slugs ``all``, ``weekdays``, and ``all-week``.
    """
    raw = (param or "today").strip().lower()
    if raw in _ATTENDANCE_REJECTED_WORKDAYS:
        raise APIError("INVALID_ATTENDANCE_WORKDAY", 400)

    valid, err = verify_attendance_workday(raw)
    if not valid:
        raise APIError(err or "INVALID_ATTENDANCE_WORKDAY", 400)

    today = camp_time.camp_today(now=now)
    if raw == "today":
        return AttendanceWorkdayContext(workday="today", camp_date=today)

    weekday_index = PART_TIME_CALENDAR_WORKDAYS.index(raw)
    monday = today - timedelta(days=today.weekday())
    camp_date = monday + timedelta(days=weekday_index)
    return AttendanceWorkdayContext(workday=raw, camp_date=camp_date)


@dataclass
class AttendanceWorkdayQuery:
    """Optional ``?workday=`` on per-person attendance history."""

    workday: str | None

    @classmethod
    def from_query(cls, args: Any) -> AttendanceWorkdayQuery:
        raw = args.get("workday")
        if raw is None:
            return cls(workday=None)
        slug = str(raw).strip().lower()
        valid, err = verify_attendance_workday(slug)
        if not valid:
            raise APIError(err or "INVALID_ATTENDANCE_WORKDAY", 400)
        return cls(workday=slug)


# ---------------------------------------------------------------------
# Attendance — mutation response (POST check-in / check-out)
# ---------------------------------------------------------------------
@dataclass
class AttendanceMutationResponse:
    employee_number: str
    camp_date: str
    checkin_at: str
    checkout_at: str | None

    @classmethod
    def from_orm(
        cls, row: Attendance, *, employee_number: str
    ) -> AttendanceMutationResponse:
        return cls(
            employee_number=employee_number,
            camp_date=row.camp_date.isoformat(),
            checkin_at=row.checkin_at.isoformat(),
            checkout_at=row.checkout_at.isoformat() if row.checkout_at else None,
        )

    def to_dict(self) -> dict:
        return {
            "employee_number": self.employee_number,
            "camp_date": self.camp_date,
            "checkin_at": self.checkin_at,
            "checkout_at": self.checkout_at,
        }


# ---------------------------------------------------------------------
# Attendance — list row (check-ins / check-outs)
# ---------------------------------------------------------------------
@dataclass
class AttendanceListEntryResponse:
    employee_number: str
    first_name: str
    last_name: str
    checkin_at: str
    checkout_at: str | None

    @classmethod
    def from_orm(cls, row: Attendance) -> AttendanceListEntryResponse:
        emp = row.employee
        return cls(
            employee_number=emp.employee_number,
            first_name=emp.first_name,
            last_name=emp.last_name,
            checkin_at=row.checkin_at.isoformat(),
            checkout_at=row.checkout_at.isoformat() if row.checkout_at else None,
        )

    def to_dict(self) -> dict:
        return {
            "employee_number": self.employee_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "checkin_at": self.checkin_at,
            "checkout_at": self.checkout_at,
        }


@dataclass
class ListCheckInsResponse:
    workday: str
    camp_date: str
    check_ins: list[AttendanceListEntryResponse]
    count: int

    def to_dict(self) -> dict:
        return {
            "workday": self.workday,
            "camp_date": self.camp_date,
            "check_ins": [row.to_dict() for row in self.check_ins],
            "count": self.count,
        }


@dataclass
class ListCheckOutsResponse:
    workday: str
    camp_date: str
    check_outs: list[AttendanceListEntryResponse]
    count: int

    def to_dict(self) -> dict:
        return {
            "workday": self.workday,
            "camp_date": self.camp_date,
            "check_outs": [row.to_dict() for row in self.check_outs],
            "count": self.count,
        }


# ---------------------------------------------------------------------
# Attendance — per-person history row / list response
# ---------------------------------------------------------------------
@dataclass
class AttendanceRowResponse:
    camp_date: str
    checkin_at: str
    checkout_at: str | None

    @classmethod
    def from_orm(cls, row: Attendance) -> AttendanceRowResponse:
        return cls(
            camp_date=row.camp_date.isoformat(),
            checkin_at=row.checkin_at.isoformat(),
            checkout_at=row.checkout_at.isoformat() if row.checkout_at else None,
        )

    def to_dict(self) -> dict:
        return {
            "camp_date": self.camp_date,
            "checkin_at": self.checkin_at,
            "checkout_at": self.checkout_at,
        }


@dataclass
class ListAttendanceResponse:
    employee_number: str
    attendances: list[AttendanceRowResponse]
    count: int
    workday: str | None = None
    camp_date: str | None = None

    def to_dict(self) -> dict:
        result = {
            "employee_number": self.employee_number,
            "attendances": [row.to_dict() for row in self.attendances],
            "count": self.count,
        }
        if self.workday is not None:
            result["workday"] = self.workday
        if self.camp_date is not None:
            result["camp_date"] = self.camp_date
        return result
