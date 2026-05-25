"""DB query encapsulation for the Employee model."""

from __future__ import annotations

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.orm import selectinload

from app.models import Company, Employee, JobAssignment, PartTime
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    # ---------------------------------------------------------------------
    # List / aggregate
    # ---------------------------------------------------------------------
    def list_with_company(
        self,
        active: bool | None,
        *,
        workday_filter: str | None = None,
        shift: str | None = None,
    ) -> list[tuple[Employee, str | None]]:
        """Employees with company name from current assignment; optional filters."""
        stmt = (
            select(Employee, Company.company_name.label("company_name"))
            .options(selectinload(Employee.part_times))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .order_by(Employee.employee_number)
        )
        stmt = self._apply_list_filters(stmt, active, workday_filter, shift)
        return list(self.db.execute(stmt).all())

    def count(
        self,
        active: bool | None,
        *,
        workday_filter: str | None = None,
        shift: str | None = None,
    ) -> int:
        """Distinct employee count matching the same filter as list_with_company."""
        stmt = (
            select(func.count(distinct(Employee.id)))
            .select_from(Employee)
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
        )
        stmt = self._apply_list_filters(stmt, active, workday_filter, shift)
        n = self.db.execute(stmt).scalar_one()
        return int(n)

    @staticmethod
    def _apply_list_filters(
        stmt,
        active: bool | None,
        workday_filter: str | None,
        shift: str | None,
    ):
        """Shared active + part-time workday/shift constraints for list and count."""
        if active is True:
            stmt = stmt.where(Employee.active.is_(True))
        elif active is False:
            stmt = stmt.where(Employee.active.is_(False))
        if workday_filter is not None:
            part_time_predicates = [PartTime.workday == workday_filter]
            if shift is not None:
                part_time_predicates.append(PartTime.shift == shift)
            stmt = stmt.where(Employee.part_times.any(and_(*part_time_predicates)))
        return stmt

    # ---------------------------------------------------------------------
    # Get one with company
    # ---------------------------------------------------------------------
    def get_with_company(
        self, employee_number: str
    ) -> tuple[Employee, str | None] | None:
        """One employee by number plus company name, or None if missing."""
        stmt = (
            select(Employee, Company.company_name.label("company_name"))
            .options(selectinload(Employee.part_times))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .where(Employee.employee_number == employee_number)
        )
        row = self.db.execute(stmt).first()
        return tuple(row) if row else None

    # ---------------------------------------------------------------------
    # Persist
    # ---------------------------------------------------------------------
    def save(self, employee: Employee) -> Employee:
        """Insert or update one employee (and nested auth); flush for id."""
        self.db.add(employee)
        self.db.flush()
        return employee

    def delete(self, employee: Employee) -> None:
        """Hard-delete one employee row."""
        self.db.delete(employee)
