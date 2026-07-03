"""Fixed camp timezone anchors and camp_time unit tests."""

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.camp_time import (
    CAMP_AFTERNOON_STARTS_AT,
    CAMP_SHIFTS,
    CampShift,
    camp_shift,
    verify_camp_shift,
)
from app.schemas.part_time import (
    PART_TIME_SHIFTS,
    PartTimeShift,
    verify_part_time_shift,
)

BERLIN = ZoneInfo("Europe/Berlin")
# Monday 2026-05-18 10:00 in Europe/Berlin
CAMP_MONDAY = datetime(2026, 5, 18, 10, 0, tzinfo=BERLIN)
# Wednesday 2026-05-20 10:00 in Europe/Berlin
CAMP_WEDNESDAY = datetime(2026, 5, 20, 10, 0, tzinfo=BERLIN)
# Friday 2026-05-22 10:00 in Europe/Berlin
CAMP_FRIDAY = datetime(2026, 5, 22, 10, 0, tzinfo=BERLIN)
# Saturday 2026-05-23 10:00 in Europe/Berlin
CAMP_SATURDAY = datetime(2026, 5, 23, 10, 0, tzinfo=BERLIN)
# Sunday 2026-05-24 10:00 in Europe/Berlin
CAMP_SUNDAY = datetime(2026, 5, 24, 10, 0, tzinfo=BERLIN)


@contextmanager
def camp_today_patch(camp_instant: datetime):
    """Pin ``camp_today()`` to a fixed calendar day in camp timezone."""

    def _fixed(*, now=None, tz=None):
        tz = tz or BERLIN
        if now is None:
            instant = camp_instant
        elif now.tzinfo is None:
            instant = now.replace(tzinfo=tz)
        else:
            instant = now.astimezone(tz)
        return instant.date()

    with patch("app.camp_time.camp_today", side_effect=_fixed):
        yield


# ---------------------------------------------------------------------
# camp_shift — afternoon boundary at 13:00 camp-local
# ---------------------------------------------------------------------
def test_camp_afternoon_starts_at_1300():
    assert CAMP_AFTERNOON_STARTS_AT == datetime(2026, 1, 1, 13, 0).time()


def test_camp_shift_morning_at_1259():
    instant = datetime(2026, 5, 20, 12, 59, tzinfo=BERLIN)
    assert camp_shift(now=instant, tz=BERLIN) == CampShift.MORNING.value


def test_camp_shift_afternoon_at_1300():
    instant = datetime(2026, 5, 20, 13, 0, tzinfo=BERLIN)
    assert camp_shift(now=instant, tz=BERLIN) == CampShift.AFTERNOON.value


def test_camp_shift_morning_at_midnight():
    instant = datetime(2026, 5, 20, 0, 0, tzinfo=BERLIN)
    assert camp_shift(now=instant, tz=BERLIN) == CampShift.MORNING.value


def test_camp_shift_afternoon_late_evening():
    instant = datetime(2026, 5, 20, 23, 59, tzinfo=BERLIN)
    assert camp_shift(now=instant, tz=BERLIN) == CampShift.AFTERNOON.value


# ---------------------------------------------------------------------
# part_time re-exports camp_time shift definitions
# ---------------------------------------------------------------------
def test_part_time_shift_is_camp_shift_alias():
    assert PartTimeShift is CampShift
    assert PART_TIME_SHIFTS == CAMP_SHIFTS
    assert verify_part_time_shift("morning") == verify_camp_shift("morning")
    assert verify_part_time_shift("invalid") == (False, "INVALID_PART_TIME_SHIFT")
