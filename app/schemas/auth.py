"""Request/response DTOs for the auth resource."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.utils import verify_access_group
from app.errors import APIError
from app.utils import validate_employee_number


# ---------------------------------------------------------------------
# Auth — login request
# ---------------------------------------------------------------------
@dataclass
class AuthenticateRequest:
    employee_number: str
    password: str

    @classmethod
    def from_dict(cls, data: Any) -> AuthenticateRequest:
        """Parse JSON body for login; raise APIError on bad input."""
        if data is None or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        for field in ("employee_number", "password"):
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        valid, err = validate_employee_number(data["employee_number"])
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)
        return cls(
            employee_number=data["employee_number"],
            password=data["password"],
        )


# ---------------------------------------------------------------------
# Auth — set auth group request
# ---------------------------------------------------------------------
@dataclass
class SetAuthGroupRequest:
    employee_number: str
    auth_group: str

    @classmethod
    def from_dict(cls, data: Any) -> SetAuthGroupRequest:
        """Parse set-auth-group body; validates checksum and access group name."""
        if data is None or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        for field in ("employee_number", "auth_group"):
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        valid, err = validate_employee_number(data["employee_number"])
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)
        valid, err = verify_access_group(data["auth_group"])
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)
        return cls(
            employee_number=data["employee_number"],
            auth_group=data["auth_group"],
        )


# ---------------------------------------------------------------------
# Auth — set password request
# ---------------------------------------------------------------------
@dataclass
class SetPasswordRequest:
    new_password: str
    old_password: str

    @classmethod
    def from_dict(cls, data: Any) -> SetPasswordRequest:
        """Parse change-password JSON (new and old password)."""
        if data is None or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        for field in ("new_password", "old_password"):
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        return cls(
            new_password=data["new_password"],
            old_password=data["old_password"],
        )


# ---------------------------------------------------------------------
# Auth — reset password request
# ---------------------------------------------------------------------
@dataclass
class ResetPasswordRequest:
    employee_number: str

    @classmethod
    def from_dict(cls, data: Any) -> ResetPasswordRequest:
        """Parse reset-password body by employee_number (checksum-checked)."""
        if data is None or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        val = data.get("employee_number")
        if val is None or (isinstance(val, str) and not val.strip()):
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        valid, err = validate_employee_number(data["employee_number"])
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)
        return cls(employee_number=data["employee_number"])


# ---------------------------------------------------------------------
# Auth — login response
# ---------------------------------------------------------------------
@dataclass
class LoginResponse:
    message: str
    token: str
    refresh_token: str
    auth_group: str
    password_must_change: bool

    def to_dict(self) -> dict:
        """JSON-ready login response mapping."""
        return {
            "message": self.message,
            "token": self.token,
            "refresh_token": self.refresh_token,
            "auth_group": self.auth_group,
            "password_must_change": self.password_must_change,
        }


# ---------------------------------------------------------------------
# Auth — set auth group response
# ---------------------------------------------------------------------
@dataclass
class SetAuthGroupResponse:
    message: str
    auth_group: str
    employee_number: str

    def to_dict(self) -> dict:
        """JSON-ready set-auth-group response mapping."""
        return {
            "message": self.message,
            "auth_group": self.auth_group,
            "employee_number": self.employee_number,
        }


# ---------------------------------------------------------------------
# Auth — refresh token response
# ---------------------------------------------------------------------
@dataclass
class RefreshResponse:
    message: str
    token: str
    employee_number: str

    def to_dict(self) -> dict:
        """JSON-ready refresh-token response mapping."""
        return {
            "message": self.message,
            "token": self.token,
            "employee_number": self.employee_number,
        }
