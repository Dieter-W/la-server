"""Errorhandler for the REST Endpoints"""

from flask import jsonify, g
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


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
        g.db.rollback()
        return jsonify({"error": "CONSTRAINT_VIOLATION", "message": f"{e}"}), 409

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        g.db.rollback()
        return jsonify({"error": "DATABASE_ERROR", "message": f"{e}"}), 500

    @app.errorhandler(Exception)
    def handle_unknown_error(e):
        g.db.rollback()
        return jsonify({"error": "INTERNAL_SERVER_ERROR", "message": f"{e}"}), 500
