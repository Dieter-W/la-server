"""DB query encapsulation for the JobAssignment model."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload

from app.models import JobAssignment
from app.repositories.base import BaseRepository


class JobAssignmentRepository(BaseRepository[JobAssignment]):
    # ---------------------------------------------------------------------
    # List / read
    # ---------------------------------------------------------------------
    def list_all(self) -> list[JobAssignment]:
        """All assignments, ordered by employee."""
        stmt = select(JobAssignment).order_by(JobAssignment.employee_id)
        return list(self.db.scalars(stmt).all())

    def get_by_employee_id(self, employee_id: int) -> JobAssignment | None:
        """Assignment for one employee, or None."""
        stmt = select(JobAssignment).where(JobAssignment.employee_id == employee_id)
        return self.db.scalars(stmt).first()

    def get_by_id(self, job_assignment_id: int) -> JobAssignment | None:
        """One assignment row by primary key, or None (employee row eager-loaded)."""
        stmt = (
            select(JobAssignment)
            .where(JobAssignment.id == job_assignment_id)
            .options(joinedload(JobAssignment.employees))
        )
        return self.db.scalars(stmt).unique().first()

    # ---------------------------------------------------------------------
    # Counts
    # ---------------------------------------------------------------------
    def count_by_company_id(self, company_id: int) -> int:
        """Number of assignments at this company."""
        stmt = select(func.count(JobAssignment.id)).where(
            JobAssignment.company_id == company_id
        )
        return int(self.db.execute(stmt).scalar_one())

    def count_all(self) -> int:
        """Total rows in job_assignments."""
        stmt = select(func.count(JobAssignment.id))
        return int(self.db.execute(stmt).scalar_one())

    # ---------------------------------------------------------------------
    # Persist — single row
    # ---------------------------------------------------------------------
    def save(self, job: JobAssignment) -> JobAssignment:
        """Add or update one row; flush so new rows get an id."""
        self.db.add(job)
        self.db.flush()
        return job

    def delete(self, job: JobAssignment) -> None:
        """Delete one assignment row."""
        self.db.delete(job)

    # ---------------------------------------------------------------------
    # Persist — bulk delete
    # ---------------------------------------------------------------------
    def delete_by_company_id(self, company_id: int) -> int:
        """Bulk-delete by company; return deleted row count."""
        stmt = delete(JobAssignment).where(JobAssignment.company_id == company_id)
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)

    def delete_all(self) -> int:
        """Delete every assignment; return deleted row count."""
        stmt = delete(JobAssignment)
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)
