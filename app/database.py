"""Database connection and session management."""

import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.peak_tracking import PeakCounter


# ---------------------------------------------------------------------
# SQLAlchemy declarative base & global ``db`` proxy
# ---------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


db = SQLAlchemy(model_class=Base)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Connection pool instrumentation
# ---------------------------------------------------------------------
def _register_pool_peak_listeners(engine, counter: PeakCounter) -> None:
    """Instrument pool checkout/checkin events for concurrency diagnostics."""

    @event.listens_for(engine.pool, "checkout")
    def _on_pool_checkout(dbapi_conn, connection_record, connection_proxy):
        """PeakCounter tick when a connection leaves the pool."""
        counter.enter()

    @event.listens_for(engine.pool, "checkin")
    def _on_pool_checkin(dbapi_conn, connection_record):
        """PeakCounter tick when a connection returns to the pool."""
        counter.leave()


# ---------------------------------------------------------------------
# Flask app initialization
# ---------------------------------------------------------------------
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
            expire_on_commit=False,
        )
        app.db_engine = engine
        app.SessionLocal = SessionLocal

        app.peak_pool_checkouts = PeakCounter()
        _register_pool_peak_listeners(engine, app.peak_pool_checkouts)

        import app.models  # noqa: F401 - register models before create_all

        # create_all ensures schema for dev, tests, and fresh installs
        # (see scripts/create_database.py for explicit bootstrap).
        db.create_all()
        logger.debug("Database schema ensured (create_all).")
