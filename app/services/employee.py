"""Business logic for the employees resource."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.auth.utils import hash_password
from app.errors import APIError
from app.models import Authentication, Employee
from app.repositories.employee import EmployeeRepository
from app.schemas.employee import (
    CreateEmployeeRequest,
    EmployeeResponse,
    UpdateEmployeeRequest,
)

logger = logging.getLogger(__name__)


class EmployeeService:
    def __init__(self, db: Session) -> None:
        """Repository for employee CRUD joined with assignment/company data."""
        self.repo = EmployeeRepository(db)

    # ---------------------------------------------------------------------
    # Employees — list
    # ---------------------------------------------------------------------
    def list_employees(self, active: bool | None) -> tuple[list[EmployeeResponse], int]:
        """List rows with resolved company column and distinct-headcount."""
        rows = self.repo.list_with_company(active)
        count = self.repo.count(active)
        responses = [
            EmployeeResponse.from_orm(emp, company_name) for emp, company_name in rows
        ]
        return responses, count

    # ---------------------------------------------------------------------
    # Employees — get one
    # ---------------------------------------------------------------------
    def get_employee(self, employee_number: str) -> EmployeeResponse:
        """GET one participant."""
        result = self.repo.get_with_company(employee_number)
        if result is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        emp, company_name = result
        return EmployeeResponse.from_orm(emp, company_name)

    # ---------------------------------------------------------------------
    # Employees — create
    # ---------------------------------------------------------------------
    def create_employee(self, req: CreateEmployeeRequest) -> EmployeeResponse:
        """Insert Employee + Authentication with temporary password."""
        emp = Employee(
            first_name=req.first_name,
            last_name=req.last_name,
            employee_number=req.employee_number,
            age=req.age,
            can_leave_alone=req.can_leave_alone,
            role=req.role,
            active=req.active,
            notes=req.notes,
            authentication=Authentication(
                auth_group=req.auth_group,
                password_must_change=True,
                password_hash=hash_password(req.last_name),
            ),
        )
        self.repo.save(emp)
        # codeql[py/clear-text-logging-sensitive-data]
        logger.info(
            "Employee created id=%s employee_number=%s", emp.id, emp.employee_number
        )
        return EmployeeResponse.from_orm(
            emp, "", auth_group=emp.authentication.auth_group
        )

    # ---------------------------------------------------------------------
    # Employees — update
    # ---------------------------------------------------------------------
    def update_employee(
        self, employee_number: str, req: UpdateEmployeeRequest
    ) -> EmployeeResponse:
        """Apply PATCH-style fields resolved by ``req`` membership."""
        result = self.repo.get_with_company(employee_number)
        if result is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        emp, company_name = result

        if "first_name" in req:
            emp.first_name = req.first_name
        if "last_name" in req:
            emp.last_name = req.last_name
        if "employee_number" in req:
            emp.employee_number = req.employee_number
        if "age" in req:
            emp.age = req.age
        if "can_leave_alone" in req:
            emp.can_leave_alone = req.can_leave_alone
        if "role" in req:
            emp.role = req.role
        if "active" in req:
            emp.active = req.active
        if "notes" in req:
            emp.notes = req.notes

        # codeql[py/clear-text-logging-sensitive-data]
        logger.info(
            "Employee updated id=%s employee_number=%s", emp.id, emp.employee_number
        )
        return EmployeeResponse.from_orm(emp, company_name)

    # ---------------------------------------------------------------------
    # Employees — soft delete (deactivate)
    # ---------------------------------------------------------------------
    def deactivate_employee(self, employee_number: str) -> EmployeeResponse:
        """Soft-delete: sets active=false, returns serialized row."""
        result = self.repo.get_with_company(employee_number)
        if result is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        emp, company_name = result
        emp.active = False
        # codeql[py/clear-text-logging-sensitive-data]
        logger.info(
            "Employee deactivated id=%s employee_number=%s", emp.id, emp.employee_number
        )
        return EmployeeResponse.from_orm(emp, company_name)

    # ---------------------------------------------------------------------
    # Employees — hard delete
    # ---------------------------------------------------------------------
    def hard_delete_employee(self, employee_number: str) -> None:
        """Remove employee row permanently."""
        result = self.repo.get_with_company(employee_number)
        if result is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        emp, _ = result
        self.repo.delete(emp)
        # codeql[py/clear-text-logging-sensitive-data]
        logger.info(
            "Employee deleted hard id=%s employee_number=%s", emp.id, employee_number
        )
