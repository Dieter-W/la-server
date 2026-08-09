"""Request/response DTOs for the part-time resource (CRUD on ``part_times`` rows)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import app.camp_time as camp_time
from app.camp_time import (
    CALENDAR_WEEKDAY_SLUGS,
    CAMP_SHIFTS,
    CampShift,
    verify_camp_shift,
)
from app.errors import APIError
from app.models import Employee, PartTime
from app.schemas import _UNSET
from app.schemas.schedule_slot import resolve_schedule_slot

# ---------------------------------------------------------------------
# Part-time primitives — enums, constants, helpers
# ---------------------------------------------------------------------
PartTimeShift = CampShift


class PartTimeWorkday(StrEnum):
    """Stored workday slug for a part-time record (calendar day or aggregate)."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    WEEKDAYS = "weekdays"
    ALL_WEEK = "all-week"


WEEKDAYS_WORKDAY = PartTimeWorkday.WEEKDAYS.value
ALL_WEEK_WORKDAY = PartTimeWorkday.ALL_WEEK.value

_PART_TIME_AGGREGATE_WORKDAYS = frozenset(
    {PartTimeWorkday.WEEKDAYS, PartTimeWorkday.ALL_WEEK}
)
PART_TIME_AGGREGATE_STORED_SLUGS = frozenset(
    {PartTimeWorkday.WEEKDAYS.value, PartTimeWorkday.ALL_WEEK.value}
)
PART_TIME_CALENDAR_WORKDAYS = list(CALENDAR_WEEKDAY_SLUGS)
PART_TIME_API_WORKDAY_LABELS = ["today", *PART_TIME_CALENDAR_WORKDAYS]
WEEKDAYS_CALENDAR_WORKDAYS = PART_TIME_CALENDAR_WORKDAYS[:5]
PART_TIME_STORED_WORKDAYS = [d.value for d in PartTimeWorkday]
PART_TIME_SHIFTS = CAMP_SHIFTS

camp_day = camp_time.camp_day
camp_instant = camp_time.camp_instant


def verify_part_time_shift(shift: str) -> tuple[bool, str | None]:
    """Verify if the part-time shift is valid (case-insensitive)."""
    return verify_camp_shift(shift)


def verify_part_time_workday(workday: str) -> tuple[bool, str | None]:
    """Verify calendar workday for list queries (case-insensitive; no aggregates)."""
    if workday.strip().lower() not in PART_TIME_CALENDAR_WORKDAYS:
        return False, "INVALID_PART_TIME_WORKDAY"

    return True, None


def verify_part_time_stored_workday(workday: str) -> tuple[bool, str | None]:
    """Verify stored workday slug including aggregate patterns (case-insensitive)."""
    if workday.strip().lower() not in PART_TIME_STORED_WORKDAYS:
        return False, "INVALID_PART_TIME_WORKDAY"

    return True, None


def validate_part_time_combination(workday: str, shift: str) -> tuple[bool, str | None]:
    """Reject aggregate workday paired with ``all-day`` (full-time = zero rows).

    Returns ``(False, "INVALID_PART_TIME_COMBINATION")`` for ``weekdays``/``all-week`` + ``all-day``.
    """
    w = workday.strip().lower()
    s = shift.strip().lower()
    if w in (WEEKDAYS_WORKDAY, ALL_WEEK_WORKDAY) and s == PartTimeShift.ALL_DAY.value:
        return False, "INVALID_PART_TIME_COMBINATION"
    return True, None


def resolve_part_time_slot(
    part_times: list[PartTime],
    lookup_workday: str,
    lookup_shift: str,
) -> PartTime | None:
    """Resolve the effective part-time row for a calendar day and shift."""
    return resolve_schedule_slot(part_times, lookup_workday, lookup_shift)


def part_time_slot_exists(
    part_times: list[PartTime],
    lookup_workday: str,
    lookup_shift: str | None = None,
) -> bool:
    """True when the employee has an effective slot for the day (and optional shift)."""
    if lookup_shift is not None:
        return (
            resolve_part_time_slot(part_times, lookup_workday, lookup_shift) is not None
        )
    morning = resolve_part_time_slot(
        part_times, lookup_workday, PartTimeShift.MORNING.value
    )
    afternoon = resolve_part_time_slot(
        part_times, lookup_workday, PartTimeShift.AFTERNOON.value
    )
    return morning is not None or afternoon is not None


def employee_is_full_time(emp: Employee) -> bool:
    """True when the participant has no ``part_times`` rows (see database design)."""
    return len(emp.part_times) == 0


@dataclass(frozen=True)
class ListWorkdayContext:
    """Resolved list ``workday`` query: filter workday, slot lookup workday, response label."""

    filter_workday: str | None
    """``None`` when ``workday=all`` (no part-time filter); else weekday for DB filter."""
    lookup_workday: str
    """Weekday used to find a ``part_times`` row on each employee."""
    response_label: str
    """API ``workday`` value when a matching slot exists (``today`` or weekday name)."""


def parse_list_workday_param(
    param: str | None,
    *,
    now: datetime | None = None,
) -> ListWorkdayContext:
    """Resolve ``GET /api/employees`` ``workday`` query (default ``all``)."""
    raw = (param or "all").strip().lower()
    today = camp_time.camp_day(now=now)

    if raw == "all":
        return ListWorkdayContext(None, today, "today")
    if raw == "today":
        return ListWorkdayContext(today, today, "today")

    valid, err = verify_part_time_workday(raw)
    if not valid:
        raise APIError(err or "INVALID_PART_TIME_WORKDAY", 400)

    return ListWorkdayContext(raw, raw, raw)


def project_api_workday_label(label: str | None) -> str | None:
    """Employee JSON ``workday``: contextual labels only — never aggregate stored slugs."""
    if label is None:
        return None
    normalized = label.strip().lower()
    if normalized in PART_TIME_AGGREGATE_STORED_SLUGS:
        return None
    if normalized == "today":
        return "today"
    if normalized in PART_TIME_CALENDAR_WORKDAYS:
        return normalized
    return None


def _resolve_projection_shift(
    part_times: list[PartTime],
    lookup_workday: str,
    *,
    explicit_shift: str | None = None,
    now: datetime | None = None,
) -> str:
    """Pick the shift slug used to project ``workday``/``shift`` on employee JSON."""
    if explicit_shift is not None:
        return explicit_shift
    today = camp_time.camp_day(now=now)
    candidates: list[str] = []
    if lookup_workday == today:
        candidates.append(camp_time.camp_shift(now=now))
    candidates.extend([PartTimeShift.MORNING.value, PartTimeShift.AFTERNOON.value])
    seen: set[str] = set()
    for shift in candidates:
        if shift in seen:
            continue
        seen.add(shift)
        if resolve_part_time_slot(part_times, lookup_workday, shift) is not None:
            return shift
    return camp_time.camp_shift(now=now)


def employee_context_workday_and_shift(
    emp: Employee,
    *,
    lookup_workday: str,
    response_label: str,
    lookup_shift: str | None = None,
    now: datetime | None = None,
) -> tuple[str | None, str | None]:
    """API ``workday`` / ``shift`` for one employee and a context weekday.

    Full-time employees (no ``part_times`` rows) get ``(response_label, "all-day")``.
    Part-time employees get ``(response_label, shift)`` when a row exists for
    ``lookup_workday`` and the resolved lookup shift (list ``?shift=``, else
    ``camp_shift()`` for today, else the first shift tier that resolves);
    otherwise ``(None, None)``.
    The ``workday`` label is never a stored aggregate slug (``weekdays``, ``all-week``).
    """
    if employee_is_full_time(emp):
        return project_api_workday_label(response_label), PartTimeShift.ALL_DAY.value
    if lookup_shift is None:
        lookup_shift = _resolve_projection_shift(
            emp.part_times, lookup_workday, now=now
        )
    pt = resolve_part_time_slot(emp.part_times, lookup_workday, lookup_shift)
    if pt is not None:
        return project_api_workday_label(response_label), pt.shift
    return None, None


def _normalize_workday(workday: str) -> str:
    """Validate and return canonical stored workday slug."""
    slug = workday.strip().lower()
    valid, err = verify_part_time_stored_workday(slug)
    if not valid:
        raise APIError(err or "INVALID_PART_TIME_WORKDAY", 400)
    return slug


def _normalize_shift(shift: str) -> str:
    """Validate and return canonical shift slug."""
    slug = shift.strip().lower()
    valid, err = verify_part_time_shift(slug)
    if not valid:
        raise APIError(err or "INVALID_PART_TIME_SHIFT", 400)
    return slug


# ---------------------------------------------------------------------
# Part-time — delete query
# ---------------------------------------------------------------------
@dataclass
class DeletePartTimeQuery:
    workday: str | None
    shift: str | None

    @classmethod
    def from_query(cls, args: Any) -> DeletePartTimeQuery:
        """Optional ``?workday=&shift=`` selects delete-one; absent means delete-all."""
        raw_workday = args.get("workday")
        raw_shift = args.get("shift")
        if raw_workday is None and raw_shift is None:
            return cls(workday=None, shift=None)
        if raw_workday is None:
            raise APIError("INVALID_PART_TIME_WORKDAY", 400)
        if raw_shift is None:
            raise APIError("INVALID_PART_TIME_SHIFT", 400)
        workday = _normalize_workday(str(raw_workday))
        shift = _normalize_shift(str(raw_shift))
        return cls(workday=workday, shift=shift)


# ---------------------------------------------------------------------
# Part-time — create request
# ---------------------------------------------------------------------
@dataclass
class CreatePartTimeRequest:
    workday: str
    shift: str = PartTimeShift.ALL_DAY.value
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> CreatePartTimeRequest:
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        workday_raw = data.get("workday")
        if workday_raw is None or (
            isinstance(workday_raw, str) and not workday_raw.strip()
        ):
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        workday = _normalize_workday(str(workday_raw))
        if "shift" in data and data["shift"] is not None:
            shift = _normalize_shift(str(data["shift"]))
        else:
            shift = PartTimeShift.ALL_DAY.value
        valid, err = validate_part_time_combination(workday, shift)
        if not valid:
            raise APIError(err or "INVALID_PART_TIME_COMBINATION", 400)
        notes = data.get("notes") if "notes" in data else None
        if notes is not None and isinstance(notes, str):
            notes = notes.strip() or None
        return cls(workday=workday, shift=shift, notes=notes)


# ---------------------------------------------------------------------
# Part-time — update request
# ---------------------------------------------------------------------
@dataclass
class UpdatePartTimeRequest:
    """Partial PUT body; ``workday`` and ``shift`` are lookup keys (not renamable)."""

    workday: str
    shift: str
    notes: Any = _UNSET

    @classmethod
    def from_dict(cls, data: dict | None) -> UpdatePartTimeRequest:
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        workday_raw = data.get("workday")
        shift_raw = data.get("shift")
        if workday_raw is None or (
            isinstance(workday_raw, str) and not workday_raw.strip()
        ):
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        if shift_raw is None or (isinstance(shift_raw, str) and not shift_raw.strip()):
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        workday = _normalize_workday(str(workday_raw))
        shift = _normalize_shift(str(shift_raw))
        notes = (data.get("notes") or None) if "notes" in data else _UNSET
        return cls(workday=workday, shift=shift, notes=notes)

    def __contains__(self, field: str) -> bool:
        return getattr(self, field, _UNSET) is not _UNSET


# ---------------------------------------------------------------------
# Part-time — row response
# ---------------------------------------------------------------------
@dataclass
class PartTimeRowResponse:
    id: int
    workday: str
    shift: str
    notes: str | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_orm(cls, row: PartTime) -> PartTimeRowResponse:
        return cls(
            id=row.id,
            workday=row.workday,
            shift=row.shift,
            notes=row.notes,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workday": self.workday,
            "shift": self.shift,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------
# Part-time — list response
# ---------------------------------------------------------------------
@dataclass
class ListPartTimesResponse:
    employee_number: str
    part_times: list[PartTimeRowResponse]
    count: int

    def to_dict(self) -> dict:
        return {
            "employee_number": self.employee_number,
            "part_times": [row.to_dict() for row in self.part_times],
            "count": self.count,
        }
