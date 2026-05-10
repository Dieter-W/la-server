"""DB query encapsulation for the Authentication model."""

from __future__ import annotations

from sqlalchemy import select

from app.models import Authentication, Employee
from app.repositories.base import BaseRepository


class AuthRepository(BaseRepository[Authentication]):
    # ---------------------------------------------------------------------
    # Reads
    # ---------------------------------------------------------------------
    def get_by_employee_number(self, employee_number: str) -> Authentication | None:
        """Auth row for an employee_number, joined through Employee; or None."""
        stmt = (
            select(Authentication)
            .join(Employee, Authentication.employee_id == Employee.id)
            .where(Employee.employee_number == employee_number)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # ---------------------------------------------------------------------
    # Session / flush
    # ---------------------------------------------------------------------
    def flush(self) -> None:
        """Flush pending ORM changes to the DB transaction."""
        self.db.flush()
