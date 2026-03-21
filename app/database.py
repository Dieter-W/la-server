"""Database connection and session management."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


db = SQLAlchemy(model_class=Base)


def init_db(app) -> None:
    """Initialize database with Flask app."""
    db.init_app(app)

    with app.app_context():
        import app.models  # noqa: F401 - register models before create_all

        db.create_all()
