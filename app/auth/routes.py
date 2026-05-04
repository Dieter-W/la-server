"""Authentication routes and endpoints for the AUTH service."""

import logging
from typing import Any

from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.auth.decorations import admin_required, staff_required, employee_required
from app.errors import APIError
from app.models import Authentication, Company, Employee, JobAssignment
from app.auth.utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_access_group,
)
from app.utils import employee_to_dict, validate_checksum

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def _validate_authenticate_payload(data: Any) -> tuple[bool, str]:
    """Validate the payload for the authenticate endpoint."""
    if data is None or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("employee_number", "password")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    valid, err = validate_checksum(data.get("employee_number"))
    if not valid:
        return False, (f"{err}_IN_JSON")

    return True, None


def _validate_set_auth_group_payload(data: Any) -> tuple[bool, str]:
    """Validate the payload for the set-auth-group endpoint."""
    if data is None or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("employee_number", "auth_group")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    valid, err = validate_checksum(data.get("employee_number"))
    if not valid:
        return False, (f"{err}_IN_JSON")

    valid, err = verify_access_group(data.get("auth_group"))
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

    valid, err = validate_checksum(data.get("employee_number"))
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
    """Authenticate a user and return tokens (public; JWT not required). The password is passed in plain text."""
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

        token_claims = {
            "auth_group": auth_employee.auth_group,
            "employee_number": auth_employee.employee.employee_number,
        }
        access_token = create_access_token(
            identity=auth_employee.id,
            additional_claims=token_claims,
        )
        refresh_token = create_refresh_token(
            identity=auth_employee.id,
            additional_claims=token_claims,
        )

    logger.info(
        "Authenticated user: %s, with auth group: %s",
        auth_employee.employee.employee_number,
        auth_employee.auth_group,
    )
    return (
        jsonify(
            {
                "message": "Authenticated",
                "token": access_token,
                "refresh_token": refresh_token,
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

        logger.debug("User: %s, with auth group: %s", employee_number, auth_group)
        return jsonify(employee_to_dict(emp, company_name, auth_group)), 200


# ---------------------------------------------------------------------
# Authentication Set auth group API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/set-auth-group", methods=["POST"])
@admin_required
def set_auth_group():
    """Set the auth group for the current user."""
    data = request.get_json(silent=True)
    valid, err = _validate_set_auth_group_payload(data)
    if not valid:
        raise APIError(err, 400)

    employee_number = data.get("employee_number")
    auth_group = data.get("auth_group")

    claims = get_jwt()
    admin_employee_number = claims.get("employee_number")

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

        auth_employee.auth_group = auth_group
        g.db.flush()

    logger.info(
        "Set auth group: %s for employee number: %s by admin employee number: %s",
        auth_group,
        employee_number,
        admin_employee_number,
    )
    return (
        jsonify(
            {
                "message": "Auth group set",
                "auth_group": auth_group,
                "employee_number": employee_number,
            }
        ),
        200,
    )


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

    logger.debug("Set password for employee number: %s", employee_number)
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
        "Reset password for employee number: %s by staff/admin employee number: %s",
        employee_number,
        staff_employee_number,
    )
    return jsonify({"message": "Password reset"}), 200


# ---------------------------------------------------------------------
# Authentication Refresh Token API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    """Issue a new access token using a valid refresh token."""

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
    """Logout the current user.

    Note: JWTs are stateless — the token remains technically valid until its
    15-minute expiry. Clients must discard the token on receipt of this response.
    For stricter invalidation, implement a server-side token blocklist.
    """
    claims = get_jwt()
    employee_number = claims.get("employee_number")
    auth_group = claims.get("auth_group")

    logger.info("Logged out user: %s, with auth group: %s", employee_number, auth_group)
    return jsonify({"message": "Logged out", "token": "INVALID-TOKEN"}), 200
