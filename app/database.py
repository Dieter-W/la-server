"""Database connection and session management."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


db = SQLAlchemy(model_class=Base)


def init_db(app) -> None:
    """Initialize database with Flask app."""
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        pool_pre_ping=True,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    app.db_engine = engine
    app.SessionLocal = SessionLocal

    db.init_app(app)

    with app.app_context():
        import app.models  # noqa: F401 - register models before create_all

        db.create_all()
