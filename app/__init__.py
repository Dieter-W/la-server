"""Kinderspielstadt Los Ämmerles - LA-Server Application."""

from flask import Flask, g

from app.database import init_db
from app.errors import register_error_handlers


def create_app(config_object=None) -> Flask:
    """Application factory."""

    app = Flask(__name__)

    if config_object:
        # Support dynamic configuration providers.
        # If `config_object` exposes `get_config()`, we use its return value so
        # env vars set right before app creation are respected.
        if hasattr(config_object, "get_config") and callable(config_object.get_config):
            app.config.from_mapping(config_object.get_config())
        else:
            app.config.from_object(config_object)

    # #region agent log
    import json

    _uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    open("debug-9015c9.log", "a").write(
        json.dumps(
            {
                "sessionId": "9015c9",
                "runId": "post-fix",
                "hypothesisId": "verify",
                "location": "app/__init__.py:create_app",
                "message": "SQLALCHEMY_DATABASE_URI type",
                "data": {"type": type(_uri).__name__, "is_str": isinstance(_uri, str)},
                "timestamp": __import__("time").time_ns() // 1_000_000,
            }
        )
        + "\n"
    )
    # #endregion

    init_db(app)

    # Session per request
    @app.before_request
    def create_session():
        g.db = app.SessionLocal()

    @app.teardown_request
    def shutdown_sessions(exception=None):
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

    register_error_handlers(app)

    from app.routes import register_routes

    register_routes(app)

    return app
