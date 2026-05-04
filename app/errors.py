"""Errorhandler for the REST Endpoints"""

import logging

from flask import current_app, jsonify, g
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message, status_code=400):
        if message is not None:
            self.message = message
        self.status_code = status_code


def register_error_handlers(app):

    @app.errorhandler(APIError)
    def handle_api_errors(e):
        return jsonify({"error": e.message}), e.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
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

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        g.db.rollback()
        logger.exception("Database error")
        body: dict = {"error": "DATABASE_ERROR"}
        if current_app.config.get("DEBUG"):
            body["message"] = str(e)
        return jsonify(body), 500

    @app.errorhandler(Exception)
    def handle_unknown_error(e):
        g.db.rollback()
        logger.exception("Unhandled error")
        body: dict = {"error": "INTERNAL_SERVER_ERROR"}
        if current_app.config.get("DEBUG"):
            body["message"] = str(e)
        return jsonify(body), 500
