"""Database connection and session management."""

import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.peak_tracking import PeakCounter

# Legacy integer until schema_metadata uses applied_hashes (compatibility hash plan).
_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------
# SQLAlchemy declarative base & global ``db`` proxy
# ---------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


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
# Schema metadata bootstrap
# ---------------------------------------------------------------------
def ensure_schema_metadata(app, *, strict: bool | None = None) -> int:
    """Seed or verify the ``schema_metadata`` singleton row.

    On a fresh database, inserts the required schema version. When a row already exists
    but its version is lower than the code constant, logs an error and raises
    in non-test environments so the server fails fast before serving traffic.

    When the row version is **newer** than ``_SCHEMA_VERSION`` (for example after a
    rollback to older server code), only an error is logged; the server keeps running
    so additive schema changes remain readable.

    There is no automatic upgrade path for ``schema_metadata.version``. After bumping
    ``_SCHEMA_VERSION`` and applying the corresponding manual migration SQL, an operator
    must update the singleton row, for example::

        UPDATE schema_metadata SET version = <new_version> WHERE id = 1;

    Returns the schema version read from the database after seed/verify.
    """
    from app.models import SCHEMA_METADATA_ROW_ID, SchemaMetadata

    if strict is None:
        strict = not app.config.get("TESTING")

    session = app.SessionLocal()
    try:
        row = session.get(SchemaMetadata, SCHEMA_METADATA_ROW_ID)
        if row is None:
            row = SchemaMetadata(id=SCHEMA_METADATA_ROW_ID, version=_SCHEMA_VERSION)
            session.add(row)
            session.commit()
            logger.info("Seeded schema_metadata with version %s.", _SCHEMA_VERSION)
            return _SCHEMA_VERSION

        if row.version < _SCHEMA_VERSION:
            msg = (
                f"Database schema version {row.version} is older than required "
                f"{_SCHEMA_VERSION}. Apply manual migration SQL and "
                f"UPDATE schema_metadata SET version = {_SCHEMA_VERSION} "
                f"WHERE id = {SCHEMA_METADATA_ROW_ID} before starting the server."
            )
            logger.error(msg)
            if strict:
                raise RuntimeError(msg)
        elif row.version > _SCHEMA_VERSION:
            logger.error(
                "Database schema version %s is newer than this server expects (%s). "
                "Rolling back server code without migrating the database is unsupported; "
                "schema_metadata.version will not be downgraded automatically.",
                row.version,
                _SCHEMA_VERSION,
            )

        return row.version
    finally:
        session.close()


# ---------------------------------------------------------------------
# Flask app initialization
# ---------------------------------------------------------------------
def init_db(app, *, create_schema: bool = True) -> None:
    """Initialize database with Flask app.

    Uses Flask-SQLAlchemy's engine (from ``SQLALCHEMY_DATABASE_URI`` and
    ``SQLALCHEMY_ENGINE_OPTIONS``) as the single pool for both ``db`` metadata
    operations and per-request ``SessionLocal`` sessions on ``g.db``.

    When ``create_schema`` is false (pytest sets ``TESTING``), schema creation
    is deferred to the test ``app`` fixture so each worker uses a fresh DB.
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

        import app.models as _models  # noqa: F401 — register models; must not shadow ``app``

        if create_schema:
            # create_all ensures schema for dev, tests, and fresh installs
            # (see scripts/create_database.py for explicit bootstrap).
            db.create_all()
            logger.debug("Database schema ensured (create_all).")
            ensure_schema_metadata(app)
