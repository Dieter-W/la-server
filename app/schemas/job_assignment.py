"""Request/response DTOs for the job_assignments resource."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.errors import APIError
from app.models import JobAssignment
from app.utils import (
    create_job_assignment_number,
    validate_employee_number,
    validate_job_assignment_number,
)


class JobAssignmentEndReason(StrEnum):
    """Why a live job assignment was archived (stored and API values)."""

    DELETED = "deleted"
    RESET_COMPANY = "reset_company"
    RESET_ALL = "reset_all"


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
        valid, err = validate_employee_number(data["employee_number"])
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
    job_assignment_id: int

    @classmethod
    def from_path(cls, job_assignment_number: str) -> DeleteJobAssignmentRequest:
        """Validate wire-format job assignment number and decode its database id."""
        ok, err, assignment_id = validate_job_assignment_number(job_assignment_number)
        if not ok or assignment_id is None:
            raise APIError(err or "JOB_ASSIGNMENT_NUMBER_WRONG", 400)
        return cls(job_assignment_id=assignment_id)


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
    job_assignment_number: str
    notes: str | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_orm(cls, job: JobAssignment) -> JobAssignmentResponse:
        """Map JobAssignment ORM row to response DTO (includes derived wire number)."""
        return cls(
            id=job.id,
            company_id=job.company_id,
            employee_id=job.employee_id,
            job_assignment_number=create_job_assignment_number(job.id),
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
            "job_assignment_number": self.job_assignment_number,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
