"""Authentication routes and endpoints for the AUTH service."""

import logging

from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.auth.decorations import admin_required, staff_required, employee_required
from app.schemas.auth import (
    AuthenticateRequest,
    ResetPasswordRequest,
    SetAuthGroupRequest,
    SetPasswordRequest,
)
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


# ---------------------------------------------------------------------
# Authentication Login API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/login", methods=["POST"])
def authenticate():
    """Authenticate a user and return tokens (public; JWT not required). The password is passed in plain text."""
    req = AuthenticateRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = AuthService(g.db).authenticate(req)
    return jsonify(response.to_dict()), 200


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
        response = AuthService(g.db).get_current_employee(employee_number, auth_group)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Authentication Set auth group API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/set-auth-group", methods=["POST"])
@admin_required
def set_auth_group():
    """Set the auth group for the current user."""
    req = SetAuthGroupRequest.from_dict(request.get_json(silent=True))
    claims = get_jwt()
    admin_employee_number = claims.get("employee_number")
    with g.db.begin():
        response = AuthService(g.db).set_auth_group(req, admin_employee_number)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Authentication Set Password API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/password/set-password", methods=["POST"])
@employee_required
def set_password():
    """Set the password for the current user."""
    req = SetPasswordRequest.from_dict(request.get_json(silent=True))
    claims = get_jwt()
    employee_number = claims.get("employee_number")
    with g.db.begin():
        AuthService(g.db).set_password(req, employee_number)
    return jsonify({"message": "Password set"}), 200


# ---------------------------------------------------------------------
# Authentication Reset Password API
# ---------------------------------------------------------------------
@auth_bp.route("/auth/password/reset-password", methods=["POST"])
@staff_required
def reset_password():
    """Reset the password for the current user."""
    req = ResetPasswordRequest.from_dict(request.get_json(silent=True))
    claims = get_jwt()
    staff_employee_number = claims.get("employee_number")
    with g.db.begin():
        AuthService(g.db).reset_password(req, staff_employee_number)
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
    identity = get_jwt_identity()
    with g.db.begin():
        response = AuthService(g.db).refresh_token(
            identity, employee_number, auth_group
        )
    return jsonify(response.to_dict()), 200


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
