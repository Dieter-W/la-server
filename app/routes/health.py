"""Health check and status endpoints."""

import os
import sys
import time

from flask import Blueprint, current_app, jsonify, g
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import QueuePool

health_bp = Blueprint("health", __name__)


def _pool_stats(engine) -> dict:
    """SQLAlchemy connection pool metrics."""
    pool = engine.pool
    if isinstance(pool, QueuePool):
        return {
            "pool_type": "QueuePool",
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "status": pool.status(),
        }
    out: dict = {"pool_type": type(pool).__name__}
    if hasattr(pool, "status"):
        try:
            out["status"] = pool.status()
        except Exception:  # pragma: no cover - defensive
            pass
    return out


def database_summary(config: dict) -> dict:
    """Redacted DB connectivity info (no credentials)."""
    uri = config.get("SQLALCHEMY_DATABASE_URI") or ""
    try:
        u = make_url(uri)
        return {
            "url_redacted": u.render_as_string(hide_password=True),
            "drivername": u.drivername,
            "host": u.host,
            "port": u.port,
            "database": u.database,
        }
    except Exception as e:
        return {"error": "could not parse database URL", "detail": str(e)}


def _runtime_info(app) -> dict:
    out = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "pid": os.getpid(),
    }
    start = getattr(app, "start_monotonic", None)
    if start is not None:
        out["uptime_seconds"] = round(time.monotonic() - start, 3)
    else:
        out["uptime_seconds"] = None
    return out


def _safe_config_snapshot(config: dict) -> dict:
    return {
        "DEBUG": config.get("DEBUG"),
        "TESTING": config.get("TESTING"),
        "LOG_LEVEL": config.get("LOG_LEVEL"),
    }


def _concurrency_snapshot(app) -> dict:
    """Peak and current counts for pool checkouts and parallel request DB sessions."""
    pool_ctr = getattr(app, "peak_pool_checkouts", None)
    req_ctr = getattr(app, "peak_request_sessions", None)
    out = {}
    if pool_ctr is not None:
        out["pool_connections"] = pool_ctr.snapshot()
    if req_ctr is not None:
        out["requests_with_db_session"] = req_ctr.snapshot()
    return out


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Basic health check endpoint."""
    return jsonify(
        {"status": "ok", "service": "Kinderspielstadt Los Ämmerles - LA-Server"}
    )


@health_bp.route("/health/db", methods=["GET"])
def db_health_check():
    """Check database connectivity."""
    try:
        g.db.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "database": str(e)}), 503


@health_bp.route("/health/runtime", methods=["GET"])
def health_runtime():
    """Operational diagnostics: pool, redacted DB URL, runtime flags (no customer data)."""
    app = current_app._get_current_object()
    return jsonify(
        {
            "service": "Kinderspielstadt Los Ämmerles - LA-Server",
            "runtime": _runtime_info(app),
            "config": _safe_config_snapshot(current_app.config),
            "database": database_summary(current_app.config),
            "concurrency": _concurrency_snapshot(app),
            "pool": _pool_stats(app.db_engine),
        }
    )
