"""Health check and status endpoints."""

from flask import Blueprint, jsonify, g
from sqlalchemy import text

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Basic health check endpoint."""
    return jsonify(
        {"status": "ok", "service": "Kinderspielstadt Los Ämmerles - LA-Server"}
    )


@health_bp.route("/health/db", methods=["GET"])
def db_health_check():
    """Check database connectivity."""
    try:
        g.db.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "database": str(e)}), 503
