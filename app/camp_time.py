"""Camp-local calendar helpers (timezone from village.ini)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.village_config import get_camp_timezone

# Order matches ``datetime.weekday()`` (0 = Monday).
CALENDAR_WEEKDAY_SLUGS: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def camp_instant(
    *, now: datetime | None = None, tz: ZoneInfo | None = None
) -> datetime:
    """Resolve a timezone-aware instant in camp timezone.

    Shared by ``camp_day`` (weekday) and ``camp_today`` (date) so the now/tz
    normalization lives in one place.
    """
    if tz is None:
        tz = get_camp_timezone()
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def camp_day(*, now: datetime | None = None, tz: ZoneInfo | None = None) -> str:
    """Current weekday (``monday`` … ``sunday``) in camp timezone."""
    instant = camp_instant(now=now, tz=tz)
    return CALENDAR_WEEKDAY_SLUGS[instant.weekday()]


def camp_today(*, now: datetime | None = None, tz: ZoneInfo | None = None) -> date:
    """Today's calendar date in camp timezone."""
    return camp_instant(now=now, tz=tz).date()
