"""Job assignment endpoints: camp participants (children and staff) take jobs at companies (*employee* names match the API)."""

import logging
import os

from flask import Blueprint, jsonify, request, g
from stdnum.iso7064 import mod_97_10

from app.errors import APIError
from app.models import Company, Employee, JobAssignment

job_assignment_bp = Blueprint("job_assignments", __name__)

logger = logging.getLogger(__name__)

VALIDATE_CHECK_SUM = os.getenv("VALIDATE_CHECK_SUM", "true").lower() == "true"


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def _job_assignment_to_dict(job: JobAssignment) -> dict:
    """Serialize job_assignment to JSON-serializable dict."""
    return {
        "id": job.id,
        "company_id": job.company_id,
        "employee_id": job.employee_id,
        "notes": job.notes,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _validate_checksum(employee_number: str) -> tuple[bool, str | None]:
    if VALIDATE_CHECK_SUM and not mod_97_10.is_valid(employee_number):
        return False, "EMPLOYEE_NUMBER_WRONG"

    return True, None


def _validate_create_payload(data: dict) -> tuple[bool, str | None]:
    """Validate POST-Create payload. Returns (valid, error_message)."""

    if not data or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("company_name", "employee_number")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    valid, err = _validate_checksum(data.get("employee_number"))
    if not valid:
        return valid, (f"{err}_IN_JSON")

    return True, None


def _validate_reset_payload(data: dict) -> tuple[bool, str | None]:
    """Validate POST-Create payload. Returns (valid, error_message)."""
    if not data:
        return True, None

    if not data or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("company_name",)
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    return True, None


# ---------------------------------------------------------------------
# Job Assignment Get-all API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments", methods=["GET"])
def list_companies():
    """List job assignments."""

    with g.db.begin():
        query = g.db.query(JobAssignment)
        job_assignments = query.order_by(JobAssignment.employee_id).all()

        return jsonify(
            {
                "job_assignments": [
                    _job_assignment_to_dict(e) for e in job_assignments
                ],
                "count": len(job_assignments),
            }
        )


# ---------------------------------------------------------------------
# Job Assignment Create API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments", methods=["POST"])
def create_job_assignment():
    """Create a new job assignment from JSON payload."""
    data = request.get_json(silent=True)
    valid, err = _validate_create_payload(data)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        comp = (
            g.db.query(Company)
            .filter(Company.company_name == data["company_name"].strip())
            .with_for_update()
            .first()
        )
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)
        if comp.active is False:
            raise APIError("COMPANY_NOT_ACTIVE", 400)

        emp = (
            g.db.query(Employee)
            .filter(Employee.employee_number == data["employee_number"].strip())
            .first()
        )
        if emp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        if emp.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        jobs = g.db.query(JobAssignment)

        has_job = jobs.filter(JobAssignment.employee_id == emp.id).first()
        if has_job:
            raise APIError("JOB_ALREADY_ASSIGNED", 400)

        assigned_count = jobs.filter(JobAssignment.company_id == comp.id).count()
        if assigned_count >= comp.jobs_max:
            raise APIError("NO_JOB_LEFT", 400)

        job_assignment = JobAssignment(
            company_id=comp.id,
            employee_id=emp.id,
        )

        g.db.add(job_assignment)
        g.db.flush()
        # High-churn: DEBUG so default INFO production logs stay readable.
        logger.debug(
            "Job assignment created id=%s company_id=%s employee_id=%s",
            job_assignment.id,
            job_assignment.company_id,
            job_assignment.employee_id,
        )
        return jsonify(_job_assignment_to_dict(job_assignment)), 201


# ---------------------------------------------------------------------
# Job Assignment Delete API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments/<string:employee_number>", methods=["DELETE"])  # fmt: skip
def delete_job_assignment(employee_number: str):
    """Delete a job assignment."""
    valid, err = _validate_checksum(employee_number)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        emp = (
            g.db.query(Employee)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if emp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        job = (
            g.db.query(JobAssignment)
            .filter(JobAssignment.employee_id == emp.id)
            .scalar()
        )
        if job is None:
            raise APIError("NO_JOB_ASSIGNED", 400)

        g.db.delete(job)
        logger.debug(
            "Job assignment deleted id=%s employee_id=%s employee_number=%s",
            job.id,
            emp.id,
            employee_number,
        )
        return jsonify({"message": "job deleted"}), 200


# ---------------------------------------------------------------------
# Job Assignment Reset API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments/reset", methods=["POST"])
def reset_job_assignment():
    """Delete a group of job assignment or all."""
    data = request.get_json(silent=True)
    valid, err = _validate_reset_payload(data)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        jobs = g.db.query(JobAssignment)

        count = jobs.count()
        if count > 0:

            if data and data["company_name"].strip():
                comp = (
                    g.db.query(Company)
                    .filter(Company.company_name == data["company_name"].strip())
                    .first()
                )

                if comp is None:
                    raise APIError("COMPANY_NOT_FOUND", 404)

                jobs = jobs.filter(JobAssignment.company_id == comp.id)
                count = jobs.count()

        reset_scope = "*"
        if data and data.get("company_name") and data["company_name"].strip():
            reset_scope = data["company_name"].strip()

        if count > 0:
            jobs.delete(synchronize_session=False)

        logger.warning(
            "Job assignments reset count=%s company_name=%s",
            count,
            reset_scope,
        )
        return (
            jsonify(
                {
                    "message": "reset successful",
                    "count": count,
                }
            ),
            200,
        )
