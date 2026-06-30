"""DB query encapsulation for the Attendance model."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import exists, select, update
from sqlalchemy.orm import joinedload

from app.models import Attendance, Employee
from app.repositories.base import BaseRepository


class AttendanceRepository(BaseRepository[Attendance]):
    # ---------------------------------------------------------------------
    # List / read
    # ---------------------------------------------------------------------
    def list_by_camp_date(self, camp_date: date) -> list[Attendance]:
        """All check-ins for one camp day, ordered by participant number."""
        stmt = (
            select(Attendance)
            .join(Attendance.employee)
            .where(Attendance.camp_date == camp_date)
            .options(joinedload(Attendance.employee))
            .order_by(Employee.employee_number)
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_checkouts_by_camp_date(self, camp_date: date) -> list[Attendance]:
        """Check-outs for one camp day (``checkout_at`` set), by participant number."""
        stmt = (
            select(Attendance)
            .join(Attendance.employee)
            .where(
                Attendance.camp_date == camp_date,
                Attendance.checkout_at.is_not(None),
            )
            .options(joinedload(Attendance.employee))
            .order_by(Employee.employee_number)
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_by_employee_id(self, employee_id: int) -> list[Attendance]:
        """Full attendance history for one participant (newest camp day first)."""
        stmt = (
            select(Attendance)
            .where(Attendance.employee_id == employee_id)
            .order_by(Attendance.camp_date.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_employee_and_date(
        self, employee_id: int, camp_date: date
    ) -> Attendance | None:
        """One row by participant and camp calendar date; or None."""
        stmt = select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.camp_date == camp_date,
        )
        return self.db.scalars(stmt).first()

    def has_checkin_for_date(self, employee_id: int, camp_date: date) -> bool:
        """True when a check-in row exists for the participant on ``camp_date``."""
        stmt = select(
            exists().where(
                Attendance.employee_id == employee_id,
                Attendance.camp_date == camp_date,
            )
        )
        return bool(self.db.scalar(stmt))

    def employee_ids_with_checkin_on_date(self, camp_date: date) -> set[int]:
        """Participant ids with a check-in row on ``camp_date`` (``checkout_at`` ignored)."""
        stmt = select(Attendance.employee_id).where(Attendance.camp_date == camp_date)
        return set(self.db.scalars(stmt).all())

    # ---------------------------------------------------------------------
    # Persist
    # ---------------------------------------------------------------------
    def save(self, row: Attendance) -> Attendance:
        """Insert or update one attendance row; flush to assign id."""
        self.db.add(row)
        self.db.flush()
        return row

    def update_checkout_if_null(
        self,
        employee_id: int,
        camp_date: date,
        checkout_at: datetime,
    ) -> int:
        """Set ``checkout_at`` only when still null; return updated row count."""
        stmt = (
            update(Attendance)
            .where(
                Attendance.employee_id == employee_id,
                Attendance.camp_date == camp_date,
                Attendance.checkout_at.is_(None),
            )
            .values(checkout_at=checkout_at)
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)
