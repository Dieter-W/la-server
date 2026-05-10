"""Request/response DTOs for the employees resource."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.utils import verify_access_group
from app.errors import APIError
from app.models import Employee
from app.schemas import _UNSET
from app.utils import validate_checksum


# ---------------------------------------------------------------------
# Employees — path parameter request
# ---------------------------------------------------------------------
@dataclass
class EmployeeNumberRequest:
    employee_number: str

    @classmethod
    def from_path(cls, employee_number: str) -> EmployeeNumberRequest:
        """Validate employee_number checksum from URL path parameter."""
        valid, err = validate_checksum(employee_number)
        if not valid:
            raise APIError(err, 400)
        return cls(employee_number=employee_number)


# ---------------------------------------------------------------------
# Employees — list query
# ---------------------------------------------------------------------
@dataclass
class ListEmployeesQuery:
    active: bool | None

    @classmethod
    def from_query(cls, args: Any) -> ListEmployeesQuery:
        value = args.get("active")
        if value is None:
            return cls(active=None)
        return cls(active=value.lower() in ("true", "1", "yes"))


# ---------------------------------------------------------------------
# Employees — delete query
# ---------------------------------------------------------------------
@dataclass
class DeleteEmployeeQuery:
    hard: bool

    @classmethod
    def from_query(cls, args: Any) -> DeleteEmployeeQuery:
        return cls(hard=args.get("hard", "").lower() in ("true", "1", "yes"))


# ---------------------------------------------------------------------
# Employees — create request
# ---------------------------------------------------------------------
@dataclass
class CreateEmployeeRequest:
    first_name: str
    last_name: str
    employee_number: str
    role: str
    auth_group: str
    active: bool = True
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> CreateEmployeeRequest:
        """Validate create-employee JSON (checksum + auth_group)."""
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        for field in (
            "first_name",
            "last_name",
            "employee_number",
            "role",
            "auth_group",
        ):
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)

        valid, err = validate_checksum(data["employee_number"])
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)

        valid, err = verify_access_group(data["auth_group"].strip().lower())
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)

        return cls(
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            employee_number=data["employee_number"].strip(),
            role=data["role"].strip(),
            auth_group=data["auth_group"].strip().lower(),
            active=data.get("active", True),
            notes=data.get("notes") or None,
        )


# ---------------------------------------------------------------------
# Employees — update request
# ---------------------------------------------------------------------
@dataclass
class UpdateEmployeeRequest:
    """Partial PUT body; ``key in req`` marks supplied fields."""

    first_name: Any = _UNSET  # str when present
    last_name: Any = _UNSET  # str when present
    employee_number: Any = _UNSET  # str when present (checksum-validated)
    role: Any = _UNSET  # str when present
    active: Any = _UNSET  # bool when present
    notes: Any = _UNSET  # str | None when present

    @classmethod
    def from_dict(cls, data: dict | None) -> UpdateEmployeeRequest:
        """Build partial-update DTO; validates new employee_number if given."""
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        employee_number = _UNSET
        if "employee_number" in data:
            valid, err = validate_checksum(data["employee_number"])
            if not valid:
                raise APIError(f"{err}_IN_JSON", 400)
            employee_number = data["employee_number"].strip()
        return cls(
            first_name=data["first_name"].strip() if "first_name" in data else _UNSET,
            last_name=data["last_name"].strip() if "last_name" in data else _UNSET,
            employee_number=employee_number,
            role=data["role"].strip() if "role" in data else _UNSET,
            active=bool(data["active"]) if "active" in data else _UNSET,
            notes=(data.get("notes") or None) if "notes" in data else _UNSET,
        )

    def __contains__(self, field: str) -> bool:
        """True if ``field`` was supplied (not _UNSET)."""
        return getattr(self, field, _UNSET) is not _UNSET


# ---------------------------------------------------------------------
# Employees — API response
# ---------------------------------------------------------------------
@dataclass
class EmployeeResponse:
    id: int
    first_name: str
    last_name: str
    employee_number: str
    role: str
    company: str
    active: bool
    notes: str | None
    created_at: str | None
    updated_at: str | None
    auth_group: str | None = None

    @classmethod
    def from_orm(cls, emp: Employee, company_name: str | None, auth_group: str | None = None) -> EmployeeResponse: # fmt: skip
        """Map Employee ORM (+ optional auth_group) to wire shape."""
        return cls(
            id=emp.id,
            first_name=emp.first_name,
            last_name=emp.last_name,
            employee_number=emp.employee_number,
            role=emp.role,
            company=company_name or "",
            active=emp.active,
            notes=emp.notes,
            created_at=emp.created_at.isoformat() if emp.created_at else None,
            updated_at=emp.updated_at.isoformat() if emp.updated_at else None,
            auth_group=auth_group,
        )

    def to_dict(self) -> dict:
        """Serialize employee payload; include auth_group only when set."""
        result = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "employee_number": self.employee_number,
            "role": self.role,
            "company": self.company,
            "active": self.active,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.auth_group is not None:
            result["auth_group"] = self.auth_group
        return result
