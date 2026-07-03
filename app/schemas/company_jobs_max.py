"""Request/response DTOs and resolution helpers for company job-capacity schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import app.camp_time as camp_time
from app.camp_time import CampShift
from app.errors import APIError
from app.models import Company, CompanyJobsMax
from app.schemas import _UNSET
from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    WEEKDAYS_WORKDAY,
    is_weekdays_calendar_day,
    project_api_workday_label,
    validate_part_time_combination,
    verify_part_time_stored_workday,
    verify_part_time_shift,
)


def verify_jobs_max(value: Any) -> int:
    """Validate schedule override cap; reject non-integers and negative values."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise APIError("INVALID_JOBS_MAX", 400)
    if value < 0:
        raise APIError("INVALID_JOBS_MAX", 400)
    return value


def resolve_company_jobs_max_slot(
    rows: list[CompanyJobsMax],
    lookup_workday: str,
    lookup_shift: str,
) -> CompanyJobsMax | None:
    """Resolve the effective schedule row for a calendar day and shift.

    Filters by ``lookup_shift`` first (``all-day`` rows never match
    ``morning``/``afternoon`` lookups), then applies workday precedence:
    calendar day > ``weekdays`` > ``all-week``.
    """
    matching_shift = [row for row in rows if row.shift == lookup_shift]
    specific = weekdays_row = all_week_row = None
    for row in matching_shift:
        if row.workday == lookup_workday:
            specific = row
        elif row.workday == WEEKDAYS_WORKDAY:
            weekdays_row = row
        elif row.workday == ALL_WEEK_WORKDAY:
            all_week_row = row
    if specific is not None:
        return specific
    if weekdays_row is not None and is_weekdays_calendar_day(lookup_workday):
        return weekdays_row
    return all_week_row


def company_uses_default_jobs_max(comp: Company) -> bool:
    """True when the company has no ``company_jobs_max`` schedule rows."""
    return len(comp.company_jobs_max) == 0


def effective_jobs_max(
    company: Company,
    *,
    lookup_workday: str | None = None,
    lookup_shift: str | None = None,
    now: datetime | None = None,
) -> int:
    """Effective job cap for camp now (or explicit workday/shift context)."""
    if lookup_workday is None:
        lookup_workday = camp_time.camp_day(now=now)
    if lookup_shift is None:
        lookup_shift = camp_time.camp_shift(now=now)

    rows = company.company_jobs_max
    if not rows:
        return company.jobs_max

    slot = resolve_company_jobs_max_slot(rows, lookup_workday, lookup_shift)
    if slot is None:
        return company.jobs_max
    return slot.jobs_max


def company_context_workday_and_shift(
    comp: Company,
    *,
    lookup_workday: str,
    lookup_shift: str,
    response_label: str = "today",
) -> tuple[bool, str | None, str | None]:
    """API ``default_jobs_max`` / ``workday`` / ``shift`` for one company.

    Zero schedule rows → ``(True, response_label, "all-day")``.
    Matching slot → ``(False, response_label, row shift)``.
    Rows exist but no match → ``(False, None, None)`` (cap falls back to default).
    """
    if company_uses_default_jobs_max(comp):
        return (
            True,
            project_api_workday_label(response_label),
            CampShift.ALL_DAY.value,
        )
    slot = resolve_company_jobs_max_slot(
        comp.company_jobs_max, lookup_workday, lookup_shift
    )
    if slot is not None:
        return (
            False,
            project_api_workday_label(response_label),
            slot.shift,
        )
    return False, None, None


def _normalize_workday(workday: str) -> str:
    slug = workday.strip().lower()
    valid, err = verify_part_time_stored_workday(slug)
    if not valid:
        raise APIError(err or "INVALID_PART_TIME_WORKDAY", 400)
    return slug


def _normalize_shift(shift: str) -> str:
    slug = shift.strip().lower()
    valid, err = verify_part_time_shift(slug)
    if not valid:
        raise APIError(err or "INVALID_PART_TIME_SHIFT", 400)
    return slug


# ---------------------------------------------------------------------
# Company jobs max — delete query
# ---------------------------------------------------------------------
@dataclass
class DeleteCompanyJobsMaxQuery:
    workday: str | None
    shift: str | None

    @classmethod
    def from_query(cls, args: Any) -> DeleteCompanyJobsMaxQuery:
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
# Company jobs max — create request
# ---------------------------------------------------------------------
@dataclass
class CreateCompanyJobsMaxRequest:
    workday: str
    jobs_max: int
    shift: str = CampShift.ALL_DAY.value
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> CreateCompanyJobsMaxRequest:
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        workday_raw = data.get("workday")
        if workday_raw is None or (
            isinstance(workday_raw, str) and not workday_raw.strip()
        ):
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        if "jobs_max" not in data or data["jobs_max"] is None:
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        workday = _normalize_workday(str(workday_raw))
        jobs_max = verify_jobs_max(data["jobs_max"])
        if "shift" in data and data["shift"] is not None:
            shift = _normalize_shift(str(data["shift"]))
        else:
            shift = CampShift.ALL_DAY.value
        valid, err = validate_part_time_combination(workday, shift)
        if not valid:
            raise APIError(err or "INVALID_PART_TIME_COMBINATION", 400)
        notes = data.get("notes") if "notes" in data else None
        if notes is not None and isinstance(notes, str):
            notes = notes.strip() or None
        return cls(workday=workday, shift=shift, jobs_max=jobs_max, notes=notes)


# ---------------------------------------------------------------------
# Company jobs max — update request
# ---------------------------------------------------------------------
@dataclass
class UpdateCompanyJobsMaxRequest:
    """Partial PUT body; ``workday`` and ``shift`` are lookup keys (not renamable)."""

    workday: str
    shift: str
    jobs_max: Any = _UNSET
    notes: Any = _UNSET

    @classmethod
    def from_dict(cls, data: dict | None) -> UpdateCompanyJobsMaxRequest:
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
        jobs_max = (
            verify_jobs_max(data["jobs_max"])
            if "jobs_max" in data and data["jobs_max"] is not None
            else _UNSET
        )
        notes = (data.get("notes") or None) if "notes" in data else _UNSET
        return cls(workday=workday, shift=shift, jobs_max=jobs_max, notes=notes)

    def __contains__(self, field: str) -> bool:
        return getattr(self, field, _UNSET) is not _UNSET


# ---------------------------------------------------------------------
# Company jobs max — row response
# ---------------------------------------------------------------------
@dataclass
class CompanyJobsMaxRowResponse:
    id: int
    workday: str
    shift: str
    jobs_max: int
    notes: str | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_orm(cls, row: CompanyJobsMax) -> CompanyJobsMaxRowResponse:
        return cls(
            id=row.id,
            workday=row.workday,
            shift=row.shift,
            jobs_max=row.jobs_max,
            notes=row.notes,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workday": self.workday,
            "shift": self.shift,
            "jobs_max": self.jobs_max,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------
# Company jobs max — list response
# ---------------------------------------------------------------------
@dataclass
class ListCompanyJobsMaxResponse:
    company_name: str
    company_jobs_max: list[CompanyJobsMaxRowResponse]
    count: int

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "company_jobs_max": [row.to_dict() for row in self.company_jobs_max],
            "count": self.count,
        }
