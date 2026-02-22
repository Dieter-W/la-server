"""Health check and status endpoints."""

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.database import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "ok", "service": "kinderspielstadt-server"})


@health_bp.route("/health/db", methods=["GET"])
def db_health_check():
    """Check database connectivity."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "database": str(e)}), 503
