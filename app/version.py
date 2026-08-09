"""Central release version and committed compatibility-hash baseline for LA-Server."""

import json
import logging
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_COMPATIBILITY_HASHES_PATH = (
    Path(__file__).resolve().parent / "compatibility_hashes.json"
)


def _read_project_version() -> str:
    """Read the canonical release version from pyproject.toml."""
    toml_path = _PROJECT_ROOT / "pyproject.toml"
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "unknown")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.warning("Could not read version from %s: %s", toml_path, exc)
        return "unknown"


def load_committed_hashes() -> dict[str, dict[str, str]]:
    """Load the reviewed compatibility-hash baseline from ``compatibility_hashes.json``.

    The file holds hash maps only (no ``server_version``) so releases never need to
    touch it. ``/api/version`` serves **computed** hashes at runtime; this reader
    supplies the committed baseline for OpenAPI examples and golden tests.

    Returns empty dicts with a warning when the file is missing or malformed.
    """
    empty: dict[str, dict[str, str]] = {
        "api_compatibility_hashes": {},
        "schema_compatibility_hashes": {},
    }
    try:
        with open(_COMPATIBILITY_HASHES_PATH, encoding="utf-8") as f:
            data: Any = json.load(f)
    except OSError as exc:
        logger.warning("Could not read %s: %s", _COMPATIBILITY_HASHES_PATH, exc)
        return empty
    except json.JSONDecodeError as exc:
        logger.warning("Malformed JSON in %s: %s", _COMPATIBILITY_HASHES_PATH, exc)
        return empty

    if not isinstance(data, dict):
        logger.warning(
            "Expected object in %s, got %s",
            _COMPATIBILITY_HASHES_PATH,
            type(data).__name__,
        )
        return empty

    api_hashes = data.get("api_compatibility_hashes")
    schema_hashes = data.get("schema_compatibility_hashes")
    if not isinstance(api_hashes, dict) or not isinstance(schema_hashes, dict):
        logger.warning(
            "Missing or invalid hash maps in %s",
            _COMPATIBILITY_HASHES_PATH,
        )
        return empty

    return {
        "api_compatibility_hashes": {
            str(key): str(value) for key, value in api_hashes.items()
        },
        "schema_compatibility_hashes": {
            str(key): str(value) for key, value in schema_hashes.items()
        },
    }


SERVER_VERSION = _read_project_version()
