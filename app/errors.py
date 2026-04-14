"""Errorhandler for the REST Endpoints"""

import logging

from flask import jsonify, g
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code


def register_error_handlers(app):

    @app.errorhandler(APIError)
    def handle_api_errors(e):
        return jsonify({"error": e.message}), e.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        msg = str(e)
        g.db.rollback()

        if "Duplicate entry" in msg:
            msg = "Create failed, because entry is already in database"

        elif "UPDATE job_assignments" in msg:
            msg = "Delete failed, because related entries in JobAssignment table"

        logger.warning("Integrity constraint: %s", msg)
        return jsonify({"error": "CONSTRAINT_VIOLATION", "message": f"{msg}"}), 409

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        g.db.rollback()
        logger.exception("Database error")
        return jsonify({"error": "DATABASE_ERROR", "message": f"{e}"}), 500

    @app.errorhandler(Exception)
    def handle_unknown_error(e):
        g.db.rollback()
        logger.exception("Unhandled error")
        return jsonify({"error": "INTERNAL_SERVER_ERROR", "message": f"{e}"}), 500
