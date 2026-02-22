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


# Add your application models here, inheriting from BaseModel
# Example:
# class Example(BaseModel):
#     __tablename__ = "examples"
#     name = db.Column(db.String(255), nullable=False)
