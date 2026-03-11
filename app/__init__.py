"""Kinderspielstadt Ammerbuch Server Application."""

from flask import Flask

from app.config import Config
from app.database import db, init_db
from app.errors import register_error_handlers


def create_app(config_class=Config) -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # #region agent log
    import json
    _uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    open("debug-9015c9.log", "a").write(
        json.dumps({"sessionId":"9015c9","runId":"post-fix","hypothesisId":"verify","location":"app/__init__.py:create_app","message":"SQLALCHEMY_DATABASE_URI type","data":{"type":type(_uri).__name__,"is_str":isinstance(_uri, str)},"timestamp":__import__("time").time_ns()//1_000_000}) + "\n"
    )
    # #endregion

    init_db(app)
    register_error_handlers(app)

    from app.routes import register_routes
    register_routes(app)

    return app
