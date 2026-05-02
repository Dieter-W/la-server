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
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Company(BaseModel):
    """Companies which offer jobs in the Spielstadt"""

    __tablename__ = "companies"
    company_name = db.Column(db.String(255), unique=True, nullable=False)
    jobs_max = db.Column(db.Integer, nullable=False)
    pay_per_hour = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    job_assignments = db.relationship("JobAssignment", back_populates="companies")


class Employee(BaseModel):
    """Camp participants (children and staff) at the Spielstadt, stored as Employee rows; soft-delete via `active`."""

    __tablename__ = "employees"

    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    employee_number = db.Column(db.String(16), unique=True, index=True, nullable=False)
    role = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    authentication = db.relationship(
        "Authentication",
        back_populates="employee",
        uselist=False,
        passive_deletes=True,
    )
    job_assignments = db.relationship("JobAssignment", back_populates="employees")


class JobAssignment(BaseModel):
    """Links camp participants (`Employee`) to companies for a placement in the Spielstadt."""

    __tablename__ = "job_assignments"
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False) # fmt: skip
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)   # fmt: skip
    notes = db.Column(db.Text, nullable=True)

    companies = db.relationship("Company", back_populates="job_assignments")
    employees = db.relationship("Employee", back_populates="job_assignments")


class Authentication(BaseModel):
    """Links camp participants (`Employee`) to a password for authentication."""

    __tablename__ = "authentications"
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False, )  # fmt: skip
    password_hash = db.Column(db.String(255), nullable=False)
    password_must_change = db.Column(db.Boolean, default=True, nullable=False)
    auth_group = db.Column(db.String(20), nullable=False, default="employee")
    notes = db.Column(db.Text, nullable=True)

    employee = db.relationship(
        "Employee", back_populates="authentication", passive_deletes=True
    )
