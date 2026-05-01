"""Decorations for the authentication routes."""

from functools import wraps
from typing import Callable

from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.errors import APIError


# ---------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------
def admin_required(fn: Callable) -> Callable:
    return _access_required(auth_groups=["admin"])(fn)


def staff_required(fn: Callable) -> Callable:
    return _access_required(auth_groups=["admin", "staff"])(fn)


def employee_required(fn: Callable) -> Callable:
    return _access_required(auth_groups=["admin", "staff", "employee"])(fn)


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def _access_required(*, auth_groups: list[str] | None = None) -> Callable:
    """Require a valid JWT. Optional ``auth_groups``: allowed ``auth_group`` values (subset)."""

    if auth_groups is None:
        allowed: list[str] | None = None
    elif isinstance(auth_groups, str):
        allowed = [auth_groups]
    elif isinstance(auth_groups, (list, tuple, set)):
        allowed = list(auth_groups)
    else:
        allowed = None

    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            jwt = get_jwt()
            auth_group = jwt.get("auth_group")

            if allowed is not None and auth_group not in allowed:
                raise APIError("FORBIDDEN_WRONG_AUTH_GROUP", 403)

            return func(*args, **kwargs)

        return decorated_function

    return wrapper
