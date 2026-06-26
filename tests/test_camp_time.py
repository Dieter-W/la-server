"""Fixed camp timezone anchors for unit and integration tests."""

from datetime import datetime
from zoneinfo import ZoneInfo

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
