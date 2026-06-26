"""DB query encapsulation for the PartTime model."""

from __future__ import annotations

from sqlalchemy import delete, select

from app.models import PartTime
from app.repositories.base import BaseRepository


class PartTimeRepository(BaseRepository[PartTime]):
    def list_by_employee_id(self, employee_id: int) -> list[PartTime]:
        """All part-time rows for one employee (unordered; service sorts)."""
        stmt = select(PartTime).where(PartTime.employee_id == employee_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_employee_and_workday(
        self, employee_id: int, workday: str
    ) -> PartTime | None:
        """One row by employee and stored workday slug; or None."""
        stmt = select(PartTime).where(
            PartTime.employee_id == employee_id,
            PartTime.workday == workday,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def save(self, row: PartTime) -> PartTime:
        """Insert or update one part-time row; flush to assign id."""
        self.db.add(row)
        self.db.flush()
        return row

    def delete(self, row: PartTime) -> None:
        """Delete one part-time row."""
        self.db.delete(row)

    def delete_all_by_employee_id(self, employee_id: int) -> int:
        """Delete all part-time rows for one employee; return deleted count."""
        stmt = (
            delete(PartTime)
            .where(PartTime.employee_id == employee_id)
            .execution_options(synchronize_session="fetch")
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)
