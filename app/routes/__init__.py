"""API routes."""

from flask import Flask


def register_routes(app: Flask) -> None:
    """Register all blueprint routes."""
    from app.auth.routes import auth_bp
    from app.routes.health import health_bp
    from app.routes.employees import employees_bp
    from app.routes.companies import companies_bp
    from app.routes.job_assignment import job_assignment_bp
    from app.routes.village_data import village_data_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(employees_bp, url_prefix="/api")
    app.register_blueprint(companies_bp, url_prefix="/api")
    app.register_blueprint(job_assignment_bp, url_prefix="/api")
    app.register_blueprint(village_data_bp, url_prefix="/api")
