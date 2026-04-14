"""Database connection and session management."""

import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


db = SQLAlchemy(model_class=Base)

logger = logging.getLogger(__name__)


def init_db(app) -> None:
    """Initialize database with Flask app.

    Uses Flask-SQLAlchemy's engine (from ``SQLALCHEMY_DATABASE_URI`` and
    ``SQLALCHEMY_ENGINE_OPTIONS``) as the single pool for both ``db`` metadata
    operations and per-request ``SessionLocal`` sessions on ``g.db``.
    """
    db.init_app(app)

    with app.app_context():
        engine = db.engine
        SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
        )
        app.db_engine = engine
        app.SessionLocal = SessionLocal

        import app.models  # noqa: F401 - register models before create_all

        db.create_all()
        logger.info("Database schema ensured (create_all).")
