"""API routes."""

from flask import Flask


def register_routes(app: Flask) -> None:
    """Register all blueprint routes."""
    from app.routes.employees import employees_bp
    from app.routes.health import health_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(employees_bp, url_prefix="/api")
