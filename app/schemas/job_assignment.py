"""Request/response DTOs for the job_assignments resource."""

from __future__ import annotations

from dataclasses import dataclass

from app.errors import APIError
from app.models import JobAssignment
from app.utils import validate_checksum


# ---------------------------------------------------------------------
# Job assignments — create request
# ---------------------------------------------------------------------
@dataclass
class CreateJobAssignmentRequest:
    company_name: str
    employee_number: str

    @classmethod
    def from_dict(cls, data: dict | None) -> CreateJobAssignmentRequest:
        """Validate create-assignment JSON (company + checksum employee number)."""
        if not data or not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        for field in ("company_name", "employee_number"):
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        valid, err = validate_checksum(data["employee_number"])
        if not valid:
            raise APIError(f"{err}_IN_JSON", 400)
        return cls(
            company_name=data["company_name"].strip(),
            employee_number=data["employee_number"].strip(),
        )


# ---------------------------------------------------------------------
# Job assignments — delete request
# ---------------------------------------------------------------------
@dataclass
class DeleteJobAssignmentRequest:
    employee_number: str

    @classmethod
    def from_path(cls, employee_number: str) -> DeleteJobAssignmentRequest:
        """Validate employee_number checksum from URL path parameter."""
        valid, err = validate_checksum(employee_number)
        if not valid:
            raise APIError(err, 400)
        return cls(employee_number=employee_number)


# ---------------------------------------------------------------------
# Job assignments — reset request
# ---------------------------------------------------------------------
@dataclass
class ResetJobAssignmentRequest:
    """Optional company_name; None means reset all assignments."""

    company_name: str | None

    @classmethod
    def from_dict(cls, data: dict | None) -> ResetJobAssignmentRequest:
        """Empty body → reset all; object body must include company_name."""
        if not data:
            return cls(company_name=None)
        if not isinstance(data, dict):
            raise APIError("REQUEST_BODY_MUST_BE_A_JSON_OBJECT", 400)
        val = data.get("company_name")
        if val is None or (isinstance(val, str) and not val.strip()):
            raise APIError("REQUIRED_JSON_INPUT_MISSING_OR_EMPTY", 400)
        return cls(company_name=val.strip())


# ---------------------------------------------------------------------
# Job assignments — API response
# ---------------------------------------------------------------------
@dataclass
class JobAssignmentResponse:
    id: int
    company_id: int
    employee_id: int
    notes: str | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_orm(cls, job: JobAssignment) -> JobAssignmentResponse:
        """Map JobAssignment ORM row to response DTO."""
        return cls(
            id=job.id,
            company_id=job.company_id,
            employee_id=job.employee_id,
            notes=job.notes,
            created_at=job.created_at.isoformat() if job.created_at else None,
            updated_at=job.updated_at.isoformat() if job.updated_at else None,
        )

    def to_dict(self) -> dict:
        """Serialize one job assignment for jsonify."""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
