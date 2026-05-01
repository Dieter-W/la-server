"""Kinderspielstadt Los Ämmerles - LA-Server Application."""

import time

from flask import Flask, g, jsonify

from app.database import init_db
from app.peak_tracking import PeakCounter
from app.errors import register_error_handlers
from app.logging_config import configure_logging


def create_app(config_object=None) -> Flask:
    """Application factory."""

    app = Flask(__name__)
    app.start_monotonic = time.monotonic()

    if config_object:
        # Support dynamic configuration providers.
        # If `config_object` exposes `get_config()`, we use its return value so
        # env vars set right before app creation are respected.
        if hasattr(config_object, "get_config") and callable(config_object.get_config):
            app.config.from_mapping(config_object.get_config())
        else:
            app.config.from_object(config_object)

    configure_logging(app)
    init_db(app)

    from flask_jwt_extended import JWTManager

    jwt = JWTManager(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "EXPIRED_TOKEN", "message": "Missing Authorization Header"}), 401 # fmt: skip

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({"error": "INVALID_TOKEN", "message": error_string}), 422 # fmt: skip

    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        return jsonify({"error": "AUTHORIZATION_REQUIRED", "message": error_string}), 401 # fmt: skip

    app.peak_request_sessions = PeakCounter()

    # Session per request
    @app.before_request
    def create_session():
        app.peak_request_sessions.enter()
        g.db = app.SessionLocal()

    @app.teardown_request
    def shutdown_sessions(exception=None):
        try:
            db = g.get("db")

            if db is None:
                return

            try:
                if exception is None:
                    db.commit()
                else:
                    db.rollback()
            finally:
                db.close()
        finally:
            app.peak_request_sessions.leave()

    register_error_handlers(app)

    from app.routes import register_routes

    register_routes(app)

    return app
