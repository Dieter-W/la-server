"""Read-only access to village.ini configuration.

Centralises file-loading (with mtime-based cache) so that both route
modules and service-layer modules can read village settings without
creating layer-crossing imports.
"""

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from app.errors import APIError

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_DEFAULT_CAMP_TIMEZONE = "Europe/Berlin"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Paths & in-memory cache
# ---------------------------------------------------------------------
# Project root (la-server/), resolved relative to this file's location.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "village_data"

_cache: dict = {
    "data": None,
    "last_updated": None,
}


# ---------------------------------------------------------------------
# INI parsing helpers
# ---------------------------------------------------------------------
def _strip_optional_ini_quotes(value: str) -> str:
    """Remove one pair of surrounding double quotes ConfigParser may preserve."""
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _ini_raw_to_dict(raw: str) -> dict:
    """Parse INI text into ``{section: {key: value}}`` with quoted values stripped.

    Only ``;`` starts an inline comment on value lines, so CSS hex colors (``#2563eb``)
    parse as full values; put trailing remarks after ``;``. Full-line ``#`` comments
    remain valid (default ``comment_prefixes``).
    """
    cp = configparser.ConfigParser(
        interpolation=None,
        inline_comment_prefixes=(";",),
    )
    try:
        cp.read_string(raw)
    except configparser.Error as e:
        logger.exception("Invalid village.ini")
        raise APIError("VILLAGE_DATA_INVALID", 500) from e
    return {
        section: {k: _strip_optional_ini_quotes(v) for k, v in cp.items(section)}
        for section in cp.sections()
    }


# ---------------------------------------------------------------------
# village.ini load & typed accessors
# ---------------------------------------------------------------------
def load_village_data() -> dict | None:
    """Load village.ini as a nested dict (JSON-serialisable), with mtime caching."""
    global _cache

    village_ini = _DATA_DIR / "village.ini"
    try:
        mtime = village_ini.stat().st_mtime
    except FileNotFoundError:
        logger.error("Village.ini not found at %s", village_ini)
        _cache["data"] = None
        return None

    if _cache["data"] is not None and mtime == _cache["last_updated"]:
        return _cache["data"]

    with open(village_ini, "r", encoding="utf-8") as f:
        raw = f.read()
        _cache["data"] = _ini_raw_to_dict(raw)
        _cache["last_updated"] = mtime
        return _cache["data"]


def get_hourly_pay_increase() -> int:
    """Return the ``hourly_pay.increase`` value from village.ini (0 if absent)."""
    village_data = load_village_data()
    if village_data:
        hourly_pay = village_data.get("hourly_pay")
        if isinstance(hourly_pay, dict):
            increase = hourly_pay.get("increase")
            if increase is not None:
                return int(increase)
    return 0


def get_camp_timezone() -> ZoneInfo:
    """Return ``general.timezone`` from village.ini as a ``ZoneInfo``.

    If the key is missing, empty, or not a valid IANA identifier, falls back to
    ``Europe/Berlin`` and logs a warning (keeps dev/test working when INI is minimal).
    """
    tz_name: str | None = None
    village_data = load_village_data()
    if village_data:
        general = village_data.get("general")
        if isinstance(general, dict):
            raw = general.get("timezone")
            if raw is not None and str(raw).strip():
                tz_name = str(raw).strip()

    if tz_name is None:
        logger.warning(
            "Missing or empty general.timezone in village.ini; using %s",
            _DEFAULT_CAMP_TIMEZONE,
        )
        return ZoneInfo(_DEFAULT_CAMP_TIMEZONE)

    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning(
            "Invalid general.timezone %r in village.ini; using %s",
            tz_name,
            _DEFAULT_CAMP_TIMEZONE,
        )
        return ZoneInfo(_DEFAULT_CAMP_TIMEZONE)


def _attendance_bool(key: str, *, default: bool) -> bool:
    """Read a boolean switch from ``[attendance]`` in village.ini."""
    village_data = load_village_data()
    if village_data:
        section = village_data.get("attendance")
        if isinstance(section, dict):
            raw = section.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip().lower() in ("true", "1", "yes")
    return default


def require_attendance_for_kids() -> bool:
    """When true, kids must check in before job assignment create/delete."""
    return _attendance_bool("require_attendance_for_kids", default=True)


def require_attendance_for_staff() -> bool:
    """When true, staff/admin must check in before job assignment create/delete."""
    return _attendance_bool("require_attendance_for_staff", default=False)
