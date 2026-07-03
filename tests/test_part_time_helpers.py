"""Shared helpers for part-time test seeding and filter parity checks."""

from __future__ import annotations

from app.models import CompanyJobsMax, Employee, PartTime
from app.schemas.part_time import (
    PART_TIME_AGGREGATE_STORED_SLUGS,
    resolve_part_time_slot,
)

PartTimeRow = tuple[int, str, str]
CompanyJobsMaxRow = tuple[int, str, str, int]


# ---------------------------------------------------------------------
# In-memory rows (unit tests)
# ---------------------------------------------------------------------
def part_time_row(workday: str, shift: str = "morning") -> PartTime:
    """In-memory part-time row for unit tests (not persisted)."""
    return PartTime(employee_id=0, workday=workday, shift=shift)


# ---------------------------------------------------------------------
# Database seeding
# ---------------------------------------------------------------------
def seed_part_time_rows(session, rows: list[PartTimeRow]) -> None:
    """Persist part-time rows and commit."""
    for employee_id, workday, shift in rows:
        session.add(PartTime(employee_id=employee_id, workday=workday, shift=shift))
    session.commit()


def seed_company_jobs_max_rows(
    session,
    rows: list[CompanyJobsMaxRow],
    *,
    notes: str | None = "Created by test script",
) -> None:
    """Persist company jobs max schedule rows and commit."""
    for company_id, workday, shift, jobs_max in rows:
        session.add(
            CompanyJobsMax(
                company_id=company_id,
                workday=workday,
                shift=shift,
                jobs_max=jobs_max,
                notes=notes,
            )
        )
    session.commit()


# ---------------------------------------------------------------------
# Employee API payload checks
# ---------------------------------------------------------------------
def assert_no_aggregate_workday_in_payload(payload: dict) -> None:
    """Stored aggregate slugs (``weekdays``, ``all-week``) must not appear in employee JSON."""
    workday = payload.get("workday")
    if workday is not None:
        assert workday not in PART_TIME_AGGREGATE_STORED_SLUGS


# ---------------------------------------------------------------------
# List filter parity
# ---------------------------------------------------------------------
def employee_matches_workday_filter(
    part_times: list[PartTime],
    filter_day: str,
    *,
    shift: str | None = None,
) -> bool:
    """True when ``resolve_part_time_slot`` would include the employee in a list filter."""
    slot = resolve_part_time_slot(part_times, filter_day)
    if slot is None:
        return False
    if shift is not None and slot.shift != shift:
        return False
    return True


def count_employees_matching_workday_filter(
    session,
    filter_day: str,
    *,
    shift: str | None = None,
) -> int:
    """Count employees whose resolved slot matches the list filter (helper truth)."""
    employees = session.query(Employee).all()
    return sum(
        1
        for employee in employees
        if employee_matches_workday_filter(
            employee.part_times,
            filter_day,
            shift=shift,
        )
    )
