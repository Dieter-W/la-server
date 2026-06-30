"""Business logic for attendance (check-in / optional check-out)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.errors import APIError
from app.models import Attendance, Employee, utc_now
from app.repositories.attendance import AttendanceRepository
from app.repositories.employee import EmployeeRepository
import app.camp_time as camp_time
from app.schemas.attendance import (
    AttendanceListEntryResponse,
    AttendanceMutationResponse,
    AttendanceRowResponse,
    AttendanceWorkdayQuery,
    ListAttendanceResponse,
    ListCheckInsResponse,
    ListCheckOutsResponse,
    resolve_attendance_workday,
)

logger = logging.getLogger(__name__)


class AttendanceService:
    def __init__(self, db: Session) -> None:
        self.employee_repo = EmployeeRepository(db)
        self.repo = AttendanceRepository(db)

    def _resolve_employee(self, employee_number: str) -> Employee:
        """Load participant by number or raise ``EMPLOYEE_NOT_FOUND``."""
        emp = self.employee_repo.get_by_number(employee_number)
        if emp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        return emp

    # ---------------------------------------------------------------------
    # Check-in / check-out (camp today only)
    # ---------------------------------------------------------------------
    def check_in(self, employee_number: str) -> AttendanceMutationResponse:
        """Record check-in for camp today; duplicate → ``409 CONSTRAINT_VIOLATION``."""
        emp = self._resolve_employee(employee_number)
        if not emp.active:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        camp_date = camp_time.camp_today()
        row = Attendance(
            employee_id=emp.id,
            camp_date=camp_date,
            checkin_at=utc_now(),
        )
        self.repo.save(row)
        logger.info(
            "Check-in recorded employee_number=%s camp_date=%s",
            employee_number,
            camp_date,
        )
        return AttendanceMutationResponse.from_orm(row, employee_number=employee_number)

    def check_out(self, employee_number: str) -> AttendanceMutationResponse:
        """Set optional check-out on today's row; no row → ``404 ATTENDANCE_NOT_CHECKED_IN``."""
        emp = self._resolve_employee(employee_number)
        camp_date = camp_time.camp_today()

        row = self.repo.get_by_employee_and_date(emp.id, camp_date)
        if row is None:
            raise APIError("ATTENDANCE_NOT_CHECKED_IN", 404)

        checkout_at = utc_now()
        updated = self.repo.update_checkout_if_null(emp.id, camp_date, checkout_at)
        if updated == 0:
            raise APIError("CONSTRAINT_VIOLATION", 409)

        logger.info(
            "Check-out recorded employee_number=%s camp_date=%s",
            employee_number,
            camp_date,
        )
        # Build the response from the known ``checkout_at`` and the row's
        # unchanged fields. Mutating ``row.checkout_at`` would mark the ORM
        # object dirty and emit a redundant second UPDATE on commit.
        return AttendanceMutationResponse(
            employee_number=employee_number,
            camp_date=row.camp_date.isoformat(),
            checkin_at=row.checkin_at.isoformat(),
            checkout_at=checkout_at.isoformat(),
        )

    # ---------------------------------------------------------------------
    # Lists (by camp day)
    # ---------------------------------------------------------------------
    def list_check_ins(self, workday: str | None = None) -> ListCheckInsResponse:
        """All check-ins for ``workday`` (default camp today), sorted by participant number."""
        ctx = resolve_attendance_workday(workday)
        rows = self.repo.list_by_camp_date(ctx.camp_date)
        entries = [AttendanceListEntryResponse.from_orm(row) for row in rows]
        return ListCheckInsResponse(
            workday=ctx.workday,
            camp_date=ctx.camp_date.isoformat(),
            check_ins=entries,
            count=len(entries),
        )

    def list_check_outs(self, workday: str | None = None) -> ListCheckOutsResponse:
        """Checked-out subset for ``workday`` (default camp today)."""
        ctx = resolve_attendance_workday(workday)
        rows = self.repo.list_checkouts_by_camp_date(ctx.camp_date)
        entries = [AttendanceListEntryResponse.from_orm(row) for row in rows]
        return ListCheckOutsResponse(
            workday=ctx.workday,
            camp_date=ctx.camp_date.isoformat(),
            check_outs=entries,
            count=len(entries),
        )

    # ---------------------------------------------------------------------
    # Per-person history
    # ---------------------------------------------------------------------
    def list_attendance(
        self,
        employee_number: str,
        query: AttendanceWorkdayQuery,
    ) -> ListAttendanceResponse:
        """Full history or one camp day when ``query.workday`` is set."""
        emp = self._resolve_employee(employee_number)

        if query.workday is None:
            rows = self.repo.list_by_employee_id(emp.id)
            responses = [AttendanceRowResponse.from_orm(row) for row in rows]
            return ListAttendanceResponse(
                employee_number=employee_number,
                attendances=responses,
                count=len(responses),
            )

        ctx = resolve_attendance_workday(query.workday)
        row = self.repo.get_by_employee_and_date(emp.id, ctx.camp_date)
        responses = [AttendanceRowResponse.from_orm(row)] if row else []
        return ListAttendanceResponse(
            employee_number=employee_number,
            attendances=responses,
            count=len(responses),
            workday=ctx.workday,
            camp_date=ctx.camp_date.isoformat(),
        )
