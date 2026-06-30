"""DB query encapsulation for the Employee model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, distinct, exists, func, or_, select
from sqlalchemy.orm import selectinload

from app.models import (
    Attendance,
    Authentication,
    Company,
    Employee,
    JobAssignment,
    PartTime,
)
from app.repositories.base import BaseRepository
from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    WEEKDAYS_WORKDAY,
    is_weekdays_calendar_day,
)


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
        checked_in: bool | None = None,
        auth_group: str | None = None,
        camp_date: date | None = None,
    ) -> list[tuple[Employee, str | None]]:
        """Employees with company name from current assignment; optional filters."""
        stmt = (
            select(Employee, Company.company_name.label("company_name"))
            .options(selectinload(Employee.part_times))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .order_by(Employee.employee_number)
        )
        stmt = self._apply_list_filters(
            stmt,
            active,
            workday_filter,
            shift,
            checked_in=checked_in,
            auth_group=auth_group,
            camp_date=camp_date,
        )
        return list(self.db.execute(stmt).all())

    def count(
        self,
        active: bool | None,
        *,
        workday_filter: str | None = None,
        shift: str | None = None,
        checked_in: bool | None = None,
        auth_group: str | None = None,
        camp_date: date | None = None,
    ) -> int:
        """Distinct employee count matching the same filter as list_with_company."""
        stmt = (
            select(func.count(distinct(Employee.id)))
            .select_from(Employee)
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
        )
        stmt = self._apply_list_filters(
            stmt,
            active,
            workday_filter,
            shift,
            checked_in=checked_in,
            auth_group=auth_group,
            camp_date=camp_date,
        )
        n = self.db.execute(stmt).scalar_one()
        return int(n)

    @staticmethod
    def _apply_list_filters(
        stmt,
        active: bool | None,
        workday_filter: str | None,
        shift: str | None,
        *,
        checked_in: bool | None = None,
        auth_group: str | None = None,
        camp_date: date | None = None,
    ):
        """Shared list/count constraints: active, part-time, attendance, auth tier."""
        if active is True:
            stmt = stmt.where(Employee.active.is_(True))
        elif active is False:
            stmt = stmt.where(Employee.active.is_(False))
        if workday_filter is not None:
            # Keep list/count SQL aligned with ``resolve_part_time_slot`` (app/schemas/employee.py):
            # direct calendar row > ``weekdays`` fallback (Mon–Fri, no calendar override) >
            # ``all-week`` fallback (no calendar override; on Mon–Fri also no ``weekdays`` row).
            # ``is_weekdays_calendar_day`` gates the weekdays branch — same helper as slot resolution.
            shift_predicates = [PartTime.shift == shift] if shift is not None else []

            direct = Employee.part_times.any(
                and_(PartTime.workday == workday_filter, *shift_predicates)
            )

            calendar_override = (
                select(PartTime.id)
                .where(
                    PartTime.employee_id == Employee.id,
                    PartTime.workday == workday_filter,
                )
                .correlate(Employee)
            )
            no_calendar_override = ~exists(calendar_override)

            weekdays_preds = [PartTime.workday == WEEKDAYS_WORKDAY, *shift_predicates]
            weekdays_fallback = and_(
                is_weekdays_calendar_day(workday_filter),
                Employee.part_times.any(and_(*weekdays_preds)),
                no_calendar_override,
            )

            weekdays_override = (
                select(PartTime.id)
                .where(
                    PartTime.employee_id == Employee.id,
                    PartTime.workday == WEEKDAYS_WORKDAY,
                )
                .correlate(Employee)
            )
            all_week_preds = [PartTime.workday == ALL_WEEK_WORKDAY, *shift_predicates]
            all_week_fallback = and_(
                Employee.part_times.any(and_(*all_week_preds)),
                no_calendar_override,
                or_(
                    not is_weekdays_calendar_day(workday_filter),
                    ~exists(weekdays_override),
                ),
            )

            stmt = stmt.where(or_(direct, weekdays_fallback, all_week_fallback))

        if checked_in is True:
            attendance_row = (
                select(Attendance.id)
                .where(
                    Attendance.employee_id == Employee.id,
                    Attendance.camp_date == camp_date,
                )
                .correlate(Employee)
            )
            stmt = stmt.where(exists(attendance_row))
        elif checked_in is False:
            attendance_row = (
                select(Attendance.id)
                .where(
                    Attendance.employee_id == Employee.id,
                    Attendance.camp_date == camp_date,
                )
                .correlate(Employee)
            )
            stmt = stmt.where(~exists(attendance_row))

        if auth_group is not None:
            stmt = stmt.outerjoin(Employee.authentication)
            if auth_group == "employee":
                stmt = stmt.where(
                    or_(
                        Authentication.auth_group == "employee",
                        Authentication.id.is_(None),
                    )
                )
            else:
                stmt = stmt.where(Authentication.auth_group == auth_group)

        return stmt

    # ---------------------------------------------------------------------
    # Get one by number (no JOIN)
    # ---------------------------------------------------------------------
    def get_by_number(self, employee_number: str) -> Employee | None:
        """One employee by number with part_times eagerly loaded; no company JOIN."""
        stmt = (
            select(Employee)
            .options(selectinload(Employee.part_times))
            .where(Employee.employee_number == employee_number)
        )
        return self.db.execute(stmt).scalar_one_or_none()

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
