"""Village data CRUD endpoints to give la-clients access to the village data."""

import configparser
import hashlib
import logging
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, send_file


from app.errors import APIError

village_data_bp = Blueprint("village_data", __name__)

logger = logging.getLogger(__name__)

# Project root (la-server/), not process cwd — same idea as app/config.py for .env.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "village_data"


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
    try:
        cp.read_string(raw)
    except configparser.Error as e:
        logger.exception("Invalid village.ini")
        raise APIError("VILLAGE_DATA_INVALID", 500) from e
    return {
        section: {k: _strip_optional_ini_quotes(v) for k, v in cp.items(section)}
        for section in cp.sections()
    }


def _file_etag(path: Path) -> str:
    """Stable ETag from file identity (mtime + size); matches hex style used for village.ini."""
    st = path.stat()
    return hashlib.md5(f"{st.st_mtime_ns}:{st.st_size}".encode()).hexdigest()


def _if_none_match_includes_etag(header_value: str | None, etag: str | None) -> bool:
    if not header_value or not etag:
        return False
    for part in header_value.split(","):
        part = part.strip()
        if part.startswith("W/"):
            part = part[2:].strip()
        if len(part) >= 2 and part[0] == '"' and part[-1] == '"':
            part = part[1:-1]
        if part == etag:
            return True
    return False


def _load_village_data():
    """Load village data from the ini file as a nested dict (JSON-serializable)."""
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
        _cache["etag"] = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return _cache["data"]


def _send_from_directory(directory: Path, relative_path: str):
    """Send a file under directory; relative_path must stay within that root."""
    base = directory.resolve()
    rel_path = Path(relative_path)
    if rel_path.is_absolute():
        logger.error("Invalid file path: %s", rel_path)
        raise APIError("INVALID_FILE_PATH", 400)
    path = (base / rel_path).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        logger.error("Invalid file path: %s", path)
        raise APIError("INVALID_FILE_PATH", 400)
    if not path.is_file():
        logger.error("File not found: %s", path)
        raise APIError("FILE_NOT_FOUND", 404)

    etag = _file_etag(path)
    if _if_none_match_includes_etag(request.headers.get("If-None-Match"), etag):
        return Response(status=304, headers={"ETag": etag})

    response = send_file(path, etag=False)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"
    return response


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

    if _if_none_match_includes_etag(request.headers.get("If-None-Match"), etag):
        return Response(status=304, headers={"ETag": etag})

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

    try:
        logo_rel = village_data["images"]["logo"]
    except KeyError:
        logger.error("Village logo not configured")
        raise APIError("VILLAGE_LOGO_NOT_CONFIGURED", 404)

    return _send_from_directory(_DATA_DIR, logo_rel)


# ---------------------------------------------------------------------
# Village Data Get image file API
# ---------------------------------------------------------------------
@village_data_bp.route("/village-data/favicon", methods=["GET"])
def get_village_data_favicon():
    """Get the favicon image file from the village data."""
    village_data = _load_village_data()
    if village_data is None:
        raise APIError("VILLAGE_DATA_NOT_FOUND", 404)

    try:
        favicon_rel = village_data["images"]["favicon"]
    except KeyError:
        logger.error("Village favicon not configured")
        raise APIError("VILLAGE_FAVICON_NOT_CONFIGURED", 404)

    return _send_from_directory(_DATA_DIR, favicon_rel)
