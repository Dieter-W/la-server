"""Request/response DTOs for the companies resource."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import app.camp_time as camp_time
from app.errors import APIError
from app.models import Company
from app.schemas import _UNSET
from app.schemas.company_jobs_max import (
    company_context_workday_and_shift,
    effective_jobs_max,
)


# ---------------------------------------------------------------------
# Companies — path parameter
# ---------------------------------------------------------------------
@dataclass
class CompanyNameRequest:
    company_name: str

    @classmethod
    def from_path(cls, company_name: str) -> CompanyNameRequest:
        name = company_name.strip()
        if not name:
            raise APIError("COMPANY_NAME_PATH_EMPTY", 400)
        return cls(company_name=name)


# ---------------------------------------------------------------------
# Companies — list query
# ---------------------------------------------------------------------
@dataclass
class ListCompaniesQuery:
    active: bool | None

    @classmethod
    def from_query(cls, args: Any) -> ListCompaniesQuery:
        value = args.get("active")
        if value is None:
            return cls(active=None)
        return cls(active=value.lower() in ("true", "1", "yes"))


# ---------------------------------------------------------------------
# Companies — create request
# ---------------------------------------------------------------------
@dataclass
class CreateCompanyRequest:
    company_name: str
    jobs_max: int
    hourly_pay: float
    active: bool = True
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> CreateCompanyRequest:
        """Validate required create fields from JSON dict."""
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        for field in ("company_name", "jobs_max", "hourly_pay"):
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        return cls(
            company_name=data["company_name"].strip(),
            jobs_max=data["jobs_max"],
            hourly_pay=data["hourly_pay"],
            active=data.get("active", True),
            notes=data.get("notes") or None,
        )


# ---------------------------------------------------------------------
# Companies — update request
# ---------------------------------------------------------------------
@dataclass
class UpdateCompanyRequest:
    """Partial PUT body; ``key in req`` marks supplied fields (see __contains__)."""

    company_name: Any = _UNSET  # str when present
    jobs_max: Any = _UNSET  # int when present
    hourly_pay: Any = _UNSET  # float when present
    active: Any = _UNSET  # bool when present
    notes: Any = _UNSET  # str | None when present

    @classmethod
    def from_dict(cls, data: dict | None) -> UpdateCompanyRequest:
        """Build partial-update DTO from JSON; omit keys leave _UNSET."""
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        return cls(
            company_name=(
                data["company_name"].strip() if "company_name" in data else _UNSET
            ),
            jobs_max=int(data["jobs_max"]) if "jobs_max" in data else _UNSET,
            hourly_pay=float(data["hourly_pay"]) if "hourly_pay" in data else _UNSET,
            active=bool(data["active"]) if "active" in data else _UNSET,
            notes=(data.get("notes") or None) if "notes" in data else _UNSET,
        )

    def __contains__(self, field: str) -> bool:
        """True if ``field`` was present in the request (not _UNSET)."""
        return getattr(self, field, _UNSET) is not _UNSET


# ---------------------------------------------------------------------
# Companies — API response
# ---------------------------------------------------------------------
@dataclass
class CompanyResponse:
    id: int
    company_name: str
    default_jobs_max: bool
    workday: str | None
    shift: str | None
    jobs: dict
    hourly_pay: float
    active: bool
    notes: str | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_orm(cls, comp: Company, assigned_jobs: int, hourly_pay_increase: int) -> CompanyResponse: # fmt: skip
        """Map Company plus aggregates to wire-shaped response model."""
        lookup_workday = camp_time.camp_day()
        lookup_shift = camp_time.camp_shift()
        default_jobs_max, workday, shift = company_context_workday_and_shift(
            comp,
            lookup_workday=lookup_workday,
            lookup_shift=lookup_shift,
            response_label="today",
        )
        jobs_max = effective_jobs_max(
            comp,
            lookup_workday=lookup_workday,
            lookup_shift=lookup_shift,
        )
        return cls(
            id=comp.id,
            company_name=comp.company_name,
            default_jobs_max=default_jobs_max,
            workday=workday,
            shift=shift,
            jobs={"available": max(0, jobs_max - assigned_jobs), "max": jobs_max},
            hourly_pay=comp.hourly_pay + hourly_pay_increase,
            active=comp.active,
            notes=comp.notes,
            created_at=comp.created_at.isoformat() if comp.created_at else None,
            updated_at=comp.updated_at.isoformat() if comp.updated_at else None,
        )

    def to_dict(self) -> dict:
        """Serialize company response for jsonify."""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "default_jobs_max": self.default_jobs_max,
            "workday": self.workday,
            "shift": self.shift,
            "jobs": self.jobs,
            "hourly_pay": self.hourly_pay,
            "active": self.active,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
