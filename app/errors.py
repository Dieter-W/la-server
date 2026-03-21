"""Errorhandler for the REST Endpoits"""

from flask import jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.database import db


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
        db.session.rollback()
        return jsonify({"error": "Contraint violation"}), 409

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        db.session.rollback()
        return jsonify({"error": "database error"}), 500

    @app.errorhandler(Exception)
    def handle_unknown_error(e):
        db.session.rollback()
        return jsonify({"error": "internal server error"}), 500
