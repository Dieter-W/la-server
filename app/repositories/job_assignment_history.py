"""DB query encapsulation for the JobAssignmentHistory model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.models import JobAssignmentHistory
from app.repositories.base import BaseRepository


class JobAssignmentHistoryRepository(BaseRepository[JobAssignmentHistory]):
    # ---------------------------------------------------------------------
    # List / read
    # ---------------------------------------------------------------------
    def list_all(
        self,
        *,
        employee_number: str | None = None,
        company_name: str | None = None,
        ended_camp_date: date | None = None,
    ) -> list[JobAssignmentHistory]:
        """All history rows with optional filters; newest ``ended_at`` first."""
        stmt = select(JobAssignmentHistory)
        if employee_number is not None:
            stmt = stmt.where(JobAssignmentHistory.employee_number == employee_number)
        if company_name is not None:
            stmt = stmt.where(JobAssignmentHistory.company_name == company_name)
        if ended_camp_date is not None:
            stmt = stmt.where(JobAssignmentHistory.ended_camp_date == ended_camp_date)
        stmt = stmt.order_by(JobAssignmentHistory.ended_at.desc())
        return list(self.db.scalars(stmt).all())

    def list_by_employee_number(
        self, employee_number: str
    ) -> list[JobAssignmentHistory]:
        """Full employment history for one participant (newest end first)."""
        stmt = (
            select(JobAssignmentHistory)
            .where(JobAssignmentHistory.employee_number == employee_number)
            .order_by(JobAssignmentHistory.ended_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    # ---------------------------------------------------------------------
    # Persist (insert-only)
    # ---------------------------------------------------------------------
    def insert(self, record: JobAssignmentHistory) -> JobAssignmentHistory:
        """Add one history row; flush to assign id."""
        self.db.add(record)
        self.db.flush()
        return record
