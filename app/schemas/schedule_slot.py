"""Shared workday + shift slot resolution for schedule rows (part-time, company jobs max)."""

from __future__ import annotations

from typing import Protocol

from app.camp_time import CALENDAR_WEEKDAY_SLUGS, CampShift

WEEKDAYS_WORKDAY = "weekdays"
ALL_WEEK_WORKDAY = "all-week"
_WEEKDAYS_CALENDAR_WORKDAYS = frozenset(CALENDAR_WEEKDAY_SLUGS[:5])


def is_weekdays_calendar_day(day: str) -> bool:
    """True when ``day`` is Monday through Friday (calendar slug only)."""
    return day.strip().lower() in _WEEKDAYS_CALENDAR_WORKDAYS


class ScheduleRow(Protocol):
    workday: str
    shift: str


def resolve_schedule_slot_for_shift[T](
    rows: list[T],
    lookup_workday: str,
    shift: str,
) -> T | None:
    """Match rows for one shift slug with workday precedence."""
    matching_shift = [row for row in rows if row.shift == shift]
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


def resolve_schedule_slot[T](
    rows: list[T],
    lookup_workday: str,
    lookup_shift: str,
) -> T | None:
    """Resolve the effective schedule row for a calendar day and shift.

    Tries an exact shift match first (``morning``/``afternoon``/``all-day``),
    then applies workday precedence: calendar day > ``weekdays`` > ``all-week``.
    For ``morning`` or ``afternoon`` lookups with no shift-specific row, falls
    back to an ``all-day`` row with the same workday precedence.
    """
    slot = resolve_schedule_slot_for_shift(rows, lookup_workday, lookup_shift)
    if slot is not None:
        return slot
    if lookup_shift in (CampShift.MORNING.value, CampShift.AFTERNOON.value):
        return resolve_schedule_slot_for_shift(
            rows, lookup_workday, CampShift.ALL_DAY.value
        )
    return None
