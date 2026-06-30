"""Business logic for the auth resource."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.auth.utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.errors import APIError
from app.repositories.attendance import AttendanceRepository
from app.repositories.auth import AuthRepository
from app.repositories.employee import EmployeeRepository
import app.camp_time as camp_time
from app.schemas.auth import (
    AuthenticateRequest,
    LoginResponse,
    RefreshResponse,
    ResetPasswordRequest,
    SetAuthGroupRequest,
    SetAuthGroupResponse,
    SetPasswordRequest,
)
from app.schemas.employee import EmployeeResponse

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        """Repos for auth lookups and employee/company joins."""
        self.auth_repo = AuthRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.attendance_repo = AttendanceRepository(db)

    # ---------------------------------------------------------------------
    # Login
    # ---------------------------------------------------------------------
    def authenticate(self, req: AuthenticateRequest) -> LoginResponse:
        """Verify credentials and return access + refresh JWT payloads."""
        auth_employee = self.auth_repo.get_by_employee_number(req.employee_number)
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)
        if not verify_password(auth_employee.password_hash, req.password):
            raise APIError("BAD_CREDENTIALS", 401)

        token_claims = {
            "auth_group": auth_employee.auth_group,
            "employee_number": auth_employee.employee.employee_number,
        }
        access_token = create_access_token(
            identity=auth_employee.id, additional_claims=token_claims
        )
        refresh_token = create_refresh_token(
            identity=auth_employee.id, additional_claims=token_claims
        )
        logger.info(
            "Authenticated user: %s, with auth group: %s",
            auth_employee.employee.employee_number,
            auth_employee.auth_group,
        )
        return LoginResponse(
            message="Authenticated",
            token=access_token,
            refresh_token=refresh_token,
            auth_group=auth_employee.auth_group,
            password_must_change=auth_employee.password_must_change,
        )

    # ---------------------------------------------------------------------
    # Current user (me)
    # ---------------------------------------------------------------------
    def get_current_employee(
        self, employee_number: str, auth_group: str
    ) -> EmployeeResponse:
        """Profile for JWT subject; rejects inactive rows."""
        result = self.employee_repo.get_with_company(employee_number)
        if result is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        emp, company_name = result
        if emp.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)
        checked_in = self.attendance_repo.has_checkin_for_date(
            emp.id, camp_time.camp_today()
        )
        logger.debug("User: %s, with auth group: %s", employee_number, auth_group)
        return EmployeeResponse.from_orm(
            emp,
            company_name,
            auth_group,
            checked_in=checked_in,
        )

    # ---------------------------------------------------------------------
    # Set auth group
    # ---------------------------------------------------------------------
    def set_auth_group(
        self, req: SetAuthGroupRequest, admin_employee_number: str
    ) -> SetAuthGroupResponse:
        """Admin writes auth_group after employee exists and active."""
        auth_employee = self.auth_repo.get_by_employee_number(req.employee_number)
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)
        auth_employee.auth_group = req.auth_group
        self.auth_repo.flush()
        logger.info(
            "Set auth group: %s for employee number: %s by admin employee number: %s",
            req.auth_group,
            req.employee_number,
            admin_employee_number,
        )
        return SetAuthGroupResponse(
            message="Auth group set",
            auth_group=req.auth_group,
            employee_number=req.employee_number,
        )

    # ---------------------------------------------------------------------
    # Set password
    # ---------------------------------------------------------------------
    def set_password(self, req: SetPasswordRequest, employee_number: str) -> None:
        """Logged-in employee changes password after old_password check."""
        auth_employee = self.auth_repo.get_by_employee_number(employee_number)
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)
        if not verify_password(auth_employee.password_hash, req.old_password):
            raise APIError("OLD_PASSWORD_IS_INCORRECT", 403)
        auth_employee.password_hash = hash_password(req.new_password)
        auth_employee.password_must_change = False
        self.auth_repo.flush()
        logger.debug("Set password for employee number: %s", employee_number)

    # ---------------------------------------------------------------------
    # Reset password
    # ---------------------------------------------------------------------
    def reset_password(
        self, req: ResetPasswordRequest, staff_employee_number: str
    ) -> None:
        """Staff resets password to hashed last name; forces change on login."""
        auth_employee = self.auth_repo.get_by_employee_number(req.employee_number)
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        auth_employee.password_must_change = True
        auth_employee.password_hash = hash_password(auth_employee.employee.last_name)
        self.auth_repo.flush()
        logger.info(
            "Reset password for employee number: %s by staff/admin employee number: %s",
            req.employee_number,
            staff_employee_number,
        )

    # ---------------------------------------------------------------------
    # Refresh token
    # ---------------------------------------------------------------------
    def refresh_token(
        self, identity: str, employee_number: str, auth_group: str
    ) -> RefreshResponse:
        """Mint a fresh access JWT if employee still exists and active."""
        auth_employee = self.auth_repo.get_by_employee_number(employee_number)
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)
        access_token = create_access_token(
            identity=identity,
            additional_claims={
                "auth_group": auth_group,
                "employee_number": employee_number,
            },
        )
        logger.debug(
            "Refreshed token for user: %s, with auth group: %s",
            employee_number,
            auth_group,
        )
        return RefreshResponse(
            message="Token refreshed",
            token=access_token,
            employee_number=employee_number,
        )
