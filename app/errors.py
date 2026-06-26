"""Errorhandler for the REST Endpoints"""

import logging

from flask import current_app, jsonify, g
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Structured API errors
# ---------------------------------------------------------------------
class APIError(Exception):
    """Raised by services/schemas to return a stable HTTP status and JSON error code."""

    message: str
    status_code: int

    def __init__(self, message: str, status_code: int = 400) -> None:
        """Store ``message`` (API error token) and HTTP ``status_code``."""
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------
# Flask error handler wiring
# ---------------------------------------------------------------------
def register_error_handlers(app):
    """Wire Flask handlers for ``APIError``, DB failures, and unhandled exceptions."""

    @app.errorhandler(APIError)
    def handle_api_errors(e):
        """Return explicit ``{"error": ...}`` body from ``APIError``."""
        return jsonify({"error": e.message}), e.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        """Map MariaDB/MySQL duplicate or FK violations to HTTP 409 JSON."""
        raw = str(e)
        g.db.rollback()

        if "Duplicate entry" in raw:
            msg = "Create failed, because entry is already in database"
        elif "UPDATE job_assignments" in raw:
            msg = "Delete failed, because related entries in JobAssignment table"
        else:
            msg = "Constraint violation"

        logger.warning("Integrity constraint: %s", raw)
        return jsonify({"error": "CONSTRAINT_VIOLATION", "message": msg}), 409

    @app.errorhandler(OperationalError)
    def handle_operational_error(e):
        """Map MariaDB concurrent row conflicts (errno 1020) to HTTP 409."""
        g.db.rollback()
        orig = getattr(e, "orig", None)
        errno = orig.args[0] if orig and getattr(orig, "args", None) else None
        if errno == 1020:
            logger.warning("Concurrent update conflict: %s", e)
            return (
                jsonify(
                    {
                        "error": "CONCURRENT_UPDATE",
                        "message": "Record changed since last read",
                    }
                ),
                409,
            )
        logger.exception("Database operational error")
        body: dict = {"error": "DATABASE_ERROR"}
        if current_app.config.get("DEBUG"):
            body["message"] = str(e)
        return jsonify(body), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        """Generic database failure; optionally includes detail when ``DEBUG`` is on."""
        g.db.rollback()
        logger.exception("Database error")
        body: dict = {"error": "DATABASE_ERROR"}
        if current_app.config.get("DEBUG"):
            body["message"] = str(e)
        return jsonify(body), 500

    @app.errorhandler(Exception)
    def handle_unknown_error(e):
        """Last-resort handler; logs stack trace and returns INTERNAL_SERVER_ERROR."""
        g.db.rollback()
        logger.exception("Unhandled error")
        body: dict = {"error": "INTERNAL_SERVER_ERROR"}
        if current_app.config.get("DEBUG"):
            body["message"] = str(e)
        return jsonify(body), 500
