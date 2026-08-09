"""Server release and API/schema compatibility hashes."""

from flask import Blueprint, jsonify

from app.contract_version import (
    compute_api_compatibility_hashes,
    compute_schema_compatibility_hashes,
)
from app.version import SERVER_VERSION

version_bp = Blueprint("version", __name__)


@version_bp.route("/version", methods=["GET"])
def get_version():
    """Return release tag and auto-computed API/schema compatibility hashes."""
    return jsonify(
        {
            "server_version": SERVER_VERSION,
            "api_compatibility_hashes": compute_api_compatibility_hashes(),
            "schema_compatibility_hashes": compute_schema_compatibility_hashes(),
        }
    )
