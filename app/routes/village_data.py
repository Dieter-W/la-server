"""Village data CRUD endpoints to give la-clients access to the village data."""

import configparser
import hashlib
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file


from app.errors import APIError

village_data_bp = Blueprint("village_data", __name__)

logger = logging.getLogger(__name__)

# Project root (la-server/), not process cwd — same idea as app/config.py for .env.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

_cache = {
    "data": None,
    "last_updated": None,
    "etag": None,
}


def _strip_optional_ini_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _ini_raw_to_dict(raw: str) -> dict:
    cp = configparser.ConfigParser()
    cp.read_string(raw)
    return {
        section: {k: _strip_optional_ini_quotes(v) for k, v in cp.items(section)}
        for section in cp.sections()
    }


def _load_village_data():
    """Load village data from the ini file as a nested dict (JSON-serializable)."""
    global _cache

    village_ini = _DATA_DIR / "village.ini"
    try:
        mtime = village_ini.stat().st_mtime
    except FileNotFoundError:
        logger.error("village.ini not found at %s", village_ini)
        _cache["data"] = None
        return None

    if _cache["data"] is not None and mtime == _cache["last_updated"]:
        return _cache["data"]

    with open(village_ini, "r", encoding="utf-8") as f:
        raw = f.read()
        _cache["data"] = _ini_raw_to_dict(raw)
        _cache["last_updated"] = mtime
        _cache["etag"] = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return _cache["data"]


def _send_from_directory(directory: Path, relative_path: str):
    """Send a file under directory; relative_path must stay within that root."""
    base = directory.resolve()
    path = (base / relative_path).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise APIError("INVALID_FILE_PATH", 400)
    if not path.is_file():
        raise APIError("FILE_NOT_FOUND", 404)
    return send_file(path)


# ---------------------------------------------------------------------
# Village Data Get API
# ---------------------------------------------------------------------
@village_data_bp.route("/village-data", methods=["GET"])
def get_village_data():
    """List village data."""
    village_data = _load_village_data()
    etag = _cache["etag"]
    if village_data is None:
        raise APIError("VILLAGE_DATA_NOT_FOUND", 404)

    if_none_match = request.headers.get("If-None-Match")
    if if_none_match == etag:
        raise APIError("NOT_MODIFIED", 304)

    return jsonify(village_data), 200, {"ETag": etag}


# ---------------------------------------------------------------------
# Village Data Get image file API
# ---------------------------------------------------------------------
@village_data_bp.route("/village-data/logo", methods=["GET"])
def get_village_data_logo():
    """Get the logo image file from the village data."""
    village_data = _load_village_data()
    if village_data is None:
        raise APIError("VILLAGE_DATA_NOT_FOUND", 404)

    # Paths in village.ini are relative to data/ (e.g. images/logo.jpg).
    return _send_from_directory(_DATA_DIR, village_data["images"]["logo"])
