"""Business logic for the part-time resource (CRUD on ``part_times`` rows)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.errors import APIError
from app.models import Employee, PartTime
from app.repositories.employee import EmployeeRepository
from app.repositories.part_time import PartTimeRepository
from app.schemas.part_time import (
    PART_TIME_STORED_WORKDAYS,
    validate_part_time_combination,
    CreatePartTimeRequest,
    ListPartTimesResponse,
    PartTimeRowResponse,
    UpdatePartTimeRequest,
)

logger = logging.getLogger(__name__)

_PART_TIME_ORDER = {slug: index for index, slug in enumerate(PART_TIME_STORED_WORKDAYS)}


class PartTimeService:
    def __init__(self, db: Session) -> None:
        self.employee_repo = EmployeeRepository(db)
        self.repo = PartTimeRepository(db)

    def _resolve_employee(self, employee_number: str) -> Employee:
        """Load employee by number or raise EMPLOYEE_NOT_FOUND."""
        emp = self.employee_repo.get_by_number(employee_number)
        if emp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        return emp

    def _sort_rows(self, rows: list[PartTime]) -> list[PartTime]:
        return sorted(rows, key=lambda row: _PART_TIME_ORDER.get(row.workday, 999))

    def list_part_times(self, employee_number: str) -> ListPartTimesResponse:
        """Return stored part-time rows ordered by PART_TIME_STORED_WORKDAYS."""
        emp = self._resolve_employee(employee_number)
        rows = self._sort_rows(self.repo.list_by_employee_id(emp.id))
        responses = [PartTimeRowResponse.from_orm(row) for row in rows]
        return ListPartTimesResponse(
            employee_number=employee_number,
            part_times=responses,
            count=len(responses),
        )

    def create_part_time(
        self, employee_number: str, req: CreatePartTimeRequest
    ) -> PartTimeRowResponse:
        """Create one part-time row.

        Uniqueness on ``(employee_id, workday)`` is enforced by the database
        constraint ``uq_part_times_employee_workday``; a duplicate surfaces as
        ``409 CONSTRAINT_VIOLATION`` via the global IntegrityError handler
        (consistent with company/employee create).
        """
        emp = self._resolve_employee(employee_number)
        row = PartTime(
            employee_id=emp.id,
            workday=req.workday,
            shift=req.shift,
            notes=req.notes,
        )
        self.repo.save(row)
        logger.info(
            "Part-time row created employee_number=%s workday=%s",
            employee_number,
            req.workday,
        )
        return PartTimeRowResponse.from_orm(row)

    def update_part_time(
        self, employee_number: str, req: UpdatePartTimeRequest
    ) -> PartTimeRowResponse:
        """Partial update by stored workday lookup key."""
        emp = self._resolve_employee(employee_number)
        row = self.repo.get_by_employee_and_workday(emp.id, req.workday)
        if row is None:
            raise APIError("PART_TIME_NOT_FOUND", 404)

        effective_shift = row.shift if "shift" not in req else req.shift
        valid, err = validate_part_time_combination(req.workday, effective_shift)
        if not valid:
            raise APIError(err or "INVALID_PART_TIME_COMBINATION", 400)

        if "shift" in req:
            row.shift = req.shift
        if "notes" in req:
            row.notes = req.notes

        logger.info(
            "Part-time row updated employee_number=%s workday=%s",
            employee_number,
            req.workday,
        )
        return PartTimeRowResponse.from_orm(row)

    def delete_all_part_times(self, employee_number: str) -> dict:
        """Delete all part-time rows (idempotent when none exist)."""
        emp = self._resolve_employee(employee_number)
        count = self.repo.delete_all_by_employee_id(emp.id)
        logger.info(
            "Part-time rows deleted employee_number=%s count=%s",
            employee_number,
            count,
        )
        return {"message": "part-time rows deleted", "count": count}

    def delete_one_part_time(self, employee_number: str, workday: str) -> dict:
        """Delete one part-time row by stored workday slug."""
        emp = self._resolve_employee(employee_number)
        row = self.repo.get_by_employee_and_workday(emp.id, workday)
        if row is None:
            raise APIError("PART_TIME_NOT_FOUND", 404)
        self.repo.delete(row)
        logger.info(
            "Part-time row deleted employee_number=%s workday=%s",
            employee_number,
            workday,
        )
        return {"message": "part-time row deleted"}
