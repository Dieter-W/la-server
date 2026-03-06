"""SQLAlchemy models for MariaDB."""

from datetime import datetime, timezone

from app.database import db


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class BaseModel(db.Model):
    """Base model with common fields."""

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Employee(BaseModel):
    """Job center employee with soft-delete support via active flag."""

    __tablename__ = "employees"

    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    employee_number = db.Column(db.String(16), unique=True, index=True, nullable=False)
    role = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
