"""DB query encapsulation for the Company model."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Company, JobAssignment
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    # ---------------------------------------------------------------------
    # List / aggregate
    # ---------------------------------------------------------------------
    def list_with_job_counts(self, active: bool | None) -> list[tuple[Company, int]]:
        """Companies with assigned-job counts; optional ``active`` filter."""
        stmt = (
            select(Company, func.count(JobAssignment.id).label("assigned_jobs"))
            .outerjoin(JobAssignment)
            .group_by(Company.id)
            .order_by(Company.company_name)
        )
        if active is True:
            stmt = stmt.where(Company.active.is_(True))
        elif active is False:
            stmt = stmt.where(Company.active.is_(False))
        return list(self.db.execute(stmt).all())

    def count(self, active: bool | None) -> int:
        """Row count for companies, with the same active filter as list."""
        stmt = select(func.count(Company.id))
        if active is True:
            stmt = stmt.where(Company.active.is_(True))
        elif active is False:
            stmt = stmt.where(Company.active.is_(False))
        return int(self.db.execute(stmt).scalar_one())

    # ---------------------------------------------------------------------
    # Get by name
    # ---------------------------------------------------------------------
    def get_by_name(self, company_name: str) -> Company | None:
        """One company by unique name; or None."""
        stmt = select(Company).where(Company.company_name == company_name)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name_with_lock(self, company_name: str) -> Company | None:
        """Like get_by_name but SELECT … FOR UPDATE for concurrent assignment."""
        stmt = (
            select(Company)
            .where(Company.company_name == company_name)
            .with_for_update()
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # ---------------------------------------------------------------------
    # Related counts
    # ---------------------------------------------------------------------
    def count_assigned_jobs(self, company_id: int) -> int:
        """How many job rows point at this company."""
        stmt = select(func.count(JobAssignment.id)).where(
            JobAssignment.company_id == company_id
        )
        return int(self.db.execute(stmt).scalar_one())

    # ---------------------------------------------------------------------
    # Persist
    # ---------------------------------------------------------------------
    def save(self, company: Company) -> Company:
        """Insert or update one company; flush to assign id."""
        self.db.add(company)
        self.db.flush()
        return company

    def delete(self, company: Company) -> None:
        """Delete one company row."""
        self.db.delete(company)
