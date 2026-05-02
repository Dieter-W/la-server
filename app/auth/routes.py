"""Authentication routes and endpoints for the AUTH service."""

import logging
import os
from typing import Any

from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import get_jwt, get_jwt_identity

from stdnum.iso7064 import mod_97_10

from app.auth.decorations import staff_required, employee_required
from app.errors import APIError
from app.models import Authentication, Company, Employee, JobAssignment
from app.auth.utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

logger = logging.getLogger(__name__)

VALIDATE_CHECK_SUM = os.getenv("VALIDATE_CHECK_SUM", "true").lower() == "true"


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def _employee_to_dict(emp: Employee, comp_name, auth_group) -> dict:
    """Serialize Employee to JSON-serializable dict."""
    return {
        "id": emp.id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "employee_number": emp.employee_number,
        "role": emp.role,
        "company": comp_name or "",
        "active": emp.active,
        "notes": emp.notes,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
        "auth_group": auth_group,
    }


def _validate_checksum(emp_num: str) -> tuple[bool, str | None]:
    """Validate the employee number. Returns (valid, error_message)."""
    if VALIDATE_CHECK_SUM and not mod_97_10.is_valid(emp_num):
        return False, "EMPLOYEE_NUMBER_WRONG"

    return True, None


def _validate_authenticate_payload(data: Any) -> tuple[bool, str]:
    """Validate the payload for the authenticate endpoint."""
    if data is None or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("employee_number", "password")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    valid, err = _validate_checksum(data.get("employee_number"))
    if not valid:
        return False, (f"{err}_IN_JSON")

    return True, None


def _validate_set_password_payload(data: Any) -> tuple[bool, str]:
    """Validate the payload for the set password endpoint."""
    if data is None or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("new_password", "old_password")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    return True, None


def _validate_reset_password_payload(data: Any) -> tuple[bool, str]:
    """Validate the payload for the reset password endpoint."""
    if data is None or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    val = data.get("employee_number")
    if val is None or (isinstance(val, str) and not val.strip()):
        return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    valid, err = _validate_checksum(data.get("employee_number"))
    if not valid:
        return False, (f"{err}_IN_JSON")

    return True, None


def _validate_token_payload(data: Any) -> tuple[bool, str]:
    """Validate the token payload."""
    if data is None or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    if not data.get("token"):
        return False, "TOKEN_IS_REQUIRED"

    return True, None


# ---------------------------------------------------------------------
# Authentication Login API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/login", methods=["POST"])
def authenticate():
    """Authenticate a user and return a token (public; JWT not required). The password is passed in plain text."""
    data = request.get_json(silent=True)
    valid, err = _validate_authenticate_payload(data)
    if not valid:
        raise APIError(err, 400)

    employee_number = data.get("employee_number")
    password_plain = data.get("password")

    with g.db.begin():
        auth_employee = (
            g.db.query(Authentication)
            .join(Employee, Authentication.employee_id == Employee.id)
            .filter(Employee.employee_number == employee_number)
            .first()
        )

        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        if not verify_password(auth_employee.password_hash, password_plain):
            raise APIError("BAD_CREDENTIALS", 401)

        access_token = create_access_token(
            identity=auth_employee.id,
            additional_claims={
                "auth_group": auth_employee.auth_group,
                "employee_number": auth_employee.employee.employee_number,
            },
        )

    logger.info(
        f"Authenticated user: {auth_employee.employee.employee_number}, with auth group: {auth_employee.auth_group}"
    )
    return (
        jsonify(
            {
                "message": "Authenticated",
                "token": access_token,
                "auth_group": auth_employee.auth_group,
                "password_must_change": auth_employee.password_must_change,
            }
        ),
        200,
    )


# ---------------------------------------------------------------------
# Authentication ME API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/me", methods=["GET"])
@employee_required
def me():
    """Return the current user."""
    claims = get_jwt()
    employee_number = claims.get("employee_number")
    auth_group = claims.get("auth_group")

    with g.db.begin():
        emp_comp = (
            g.db.query(Employee, Company.company_name.label("company_name"))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if emp_comp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        emp, company_name = emp_comp

        if emp.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        logger.debug(f"User: {employee_number}, with auth group: {auth_group}")
        return jsonify(_employee_to_dict(emp, company_name, auth_group)), 200


# ---------------------------------------------------------------------
# Authentication Set Password API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/password/set-password", methods=["POST"])
@employee_required
def set_password():
    """Set the password for the current user."""
    data = request.get_json(silent=True)
    valid, err = _validate_set_password_payload(data)
    if not valid:
        raise APIError(err, 400)

    claims = get_jwt()
    employee_number = claims.get("employee_number")

    with g.db.begin():
        auth_employee = (
            g.db.query(Authentication)
            .join(Employee, Authentication.employee_id == Employee.id)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        if not verify_password(auth_employee.password_hash, data.get("old_password")):
            raise APIError("OLD_PASSWORD_IS_INCORRECT", 403)

        auth_employee.password_hash = hash_password(data.get("new_password"))
        auth_employee.password_must_change = False
        g.db.flush()

    logger.debug(f"Set password for employee number: {employee_number}")
    return jsonify({"message": "Password set"}), 200


# ---------------------------------------------------------------------
# Authentication Reset Password API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/password/reset-password", methods=["POST"])
@staff_required
def reset_password():
    """Reset the password for the current user."""
    data = request.get_json(silent=True)
    valid, err = _validate_reset_password_payload(data)
    if not valid:
        raise APIError(err, 400)

    employee_number = data.get("employee_number")

    claims = get_jwt()
    staff_employee_number = claims.get("employee_number")

    with g.db.begin():
        auth_employee = (
            g.db.query(Authentication)
            .join(Employee, Authentication.employee_id == Employee.id)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        auth_employee.password_must_change = True
        auth_employee.password_hash = hash_password(auth_employee.employee.last_name)
        g.db.flush()

    logger.info(
        f"Reset password for employee number: {employee_number} by staff/admin employee number: {staff_employee_number}"
    )
    return jsonify({"message": "Password reset"}), 200


# ---------------------------------------------------------------------
# Authentication Refresh Token API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/refresh", methods=["POST"])
@employee_required
def refresh_token():
    """Refresh the token for the current user."""

    claims = get_jwt()
    employee_number = claims.get("employee_number")
    auth_group = claims.get("auth_group")

    with g.db.begin():
        auth_employee = (
            g.db.query(Authentication)
            .join(Employee, Authentication.employee_id == Employee.id)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if auth_employee is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        if auth_employee.employee.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        identity = get_jwt_identity()
        access_token = create_refresh_token(
            identity=identity,
            additional_claims={
                "auth_group": auth_group,
                "employee_number": employee_number,
            },
        )

    logger.debug(
        f"Refreshed token for user: {employee_number}, with auth group: {auth_group}"
    )
    return (
        jsonify(
            {
                "message": "Token refreshed",
                "token": access_token,
                "employee_number": employee_number,
            }
        ),
        200,
    )


# ---------------------------------------------------------------------
# Authentication Logout API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/logout", methods=["POST"])
@employee_required
def logout():
    """Logout the current user."""
    claims = get_jwt()
    employee_number = claims.get("employee_number")
    auth_group = claims.get("auth_group")

    logger.info(f"Logged out user: {employee_number}, with auth group: {auth_group}")
    return jsonify({"message": "Logged out", "token": "INVALID-TOKEN"}), 200
