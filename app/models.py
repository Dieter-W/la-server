"""SQLAlchemy models for MariaDB."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import db


# ---------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------
def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------
class BaseModel(db.Model):
    """Base model with common fields."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


# ---------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------
class Authentication(BaseModel):
    """Participant login credentials (one row per employee)."""

    __tablename__ = "authentications"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    password_must_change: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_group: Mapped[str] = mapped_column(String(20), default="employee")
    notes: Mapped[str | None] = mapped_column(Text)

    employee: Mapped[Employee] = relationship(
        back_populates="authentication",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------
class Company(BaseModel):
    """Companies which offer jobs in the Spielstadt."""

    __tablename__ = "companies"

    company_name: Mapped[str] = mapped_column(String(255), unique=True)
    jobs_max: Mapped[int] = mapped_column(Integer, default=0)
    hourly_pay: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    job_assignments: Mapped[list[JobAssignment]] = relationship(
        back_populates="companies",
    )
    company_jobs_max: Mapped[list[CompanyJobsMax]] = relationship(
        back_populates="company",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------
# Company jobs max
# ---------------------------------------------------------------------
class CompanyJobsMax(BaseModel):
    """Workday + shift override for a company's job capacity."""

    __tablename__ = "company_jobs_max"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "workday",
            "shift",
            name="uq_company_jobs_max_company_workday_shift",
        ),
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
    )
    workday: Mapped[str] = mapped_column(String(20))
    shift: Mapped[str] = mapped_column(String(20), default="all-day")
    jobs_max: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(
        back_populates="company_jobs_max",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------
class Employee(BaseModel):
    """Camp participants at the Spielstadt; soft-delete via ``active``."""

    __tablename__ = "employees"

    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    employee_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    can_leave_alone: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    authentication: Mapped[Authentication | None] = relationship(
        back_populates="employee",
        uselist=False,
        passive_deletes=True,
    )
    job_assignments: Mapped[list[JobAssignment]] = relationship(
        back_populates="employees",
    )
    part_times: Mapped[list[PartTime]] = relationship(
        back_populates="employee",
        passive_deletes=True,
    )
    attendances: Mapped[list[Attendance]] = relationship(
        back_populates="employee",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------
# Job assignment
# ---------------------------------------------------------------------
class JobAssignment(BaseModel):
    """Links participants (``Employee``) to companies for a Spielstadt placement."""

    __tablename__ = "job_assignments"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"),
    )
    notes: Mapped[str | None] = mapped_column(Text)

    companies: Mapped[Company] = relationship(back_populates="job_assignments")
    employees: Mapped[Employee] = relationship(back_populates="job_assignments")


# ---------------------------------------------------------------------
# Part-time
# ---------------------------------------------------------------------
class PartTime(BaseModel):
    """Part-time schedule slot for one weekday (and optional shift)."""

    __tablename__ = "part_times"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "workday",
            name="uq_part_times_employee_workday",
        ),
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
    )
    workday: Mapped[str] = mapped_column(String(20))
    shift: Mapped[str] = mapped_column(String(20), default="all-day")

    notes: Mapped[str | None] = mapped_column(Text)

    employee: Mapped[Employee] = relationship(
        back_populates="part_times",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------
class Attendance(BaseModel):
    """Daily check-in / optional check-out for one camp participant."""

    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "camp_date",
            name="uq_attendances_employee_camp_date",
        ),
        Index("ix_attendances_camp_date", "camp_date"),
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
    )
    camp_date: Mapped[date] = mapped_column(Date)
    checkin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checkout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    employee: Mapped[Employee] = relationship(
        back_populates="attendances",
        passive_deletes=True,
    )
