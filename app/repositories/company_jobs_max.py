"""DB query encapsulation for the CompanyJobsMax model."""

from __future__ import annotations

from sqlalchemy import delete, select

from app.models import CompanyJobsMax
from app.repositories.base import BaseRepository


class CompanyJobsMaxRepository(BaseRepository[CompanyJobsMax]):
    def list_by_company_id(self, company_id: int) -> list[CompanyJobsMax]:
        """All schedule rows for one company (unordered; service sorts)."""
        stmt = select(CompanyJobsMax).where(CompanyJobsMax.company_id == company_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_company_workday_shift(
        self, company_id: int, workday: str, shift: str
    ) -> CompanyJobsMax | None:
        """One row by company and stored workday/shift keys; or None."""
        stmt = select(CompanyJobsMax).where(
            CompanyJobsMax.company_id == company_id,
            CompanyJobsMax.workday == workday,
            CompanyJobsMax.shift == shift,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def save(self, row: CompanyJobsMax) -> CompanyJobsMax:
        """Insert or update one schedule row; flush to assign id."""
        self.db.add(row)
        self.db.flush()
        return row

    def delete(self, row: CompanyJobsMax) -> None:
        """Delete one schedule row."""
        self.db.delete(row)

    def delete_all_by_company_id(self, company_id: int) -> int:
        """Delete all schedule rows for one company; return deleted count."""
        stmt = (
            delete(CompanyJobsMax)
            .where(CompanyJobsMax.company_id == company_id)
            .execution_options(synchronize_session="fetch")
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)
