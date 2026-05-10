"""Job assignment endpoints: camp participants (children and staff) take jobs at companies (*employee* names match the API)."""

from flask import Blueprint, jsonify, request, g

from app.auth.decorations import admin_required, employee_required
from app.schemas.job_assignment import (
    CreateJobAssignmentRequest,
    DeleteJobAssignmentRequest,
    ResetJobAssignmentRequest,
)
from app.services.job_assignment import JobAssignmentService

job_assignment_bp = Blueprint("job_assignments", __name__)


# ---------------------------------------------------------------------
# Job Assignment Get-all API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments", methods=["GET"])
def list_job_assignments():
    """List job assignments."""
    with g.db.begin():
        service = JobAssignmentService(g.db)
        assignments, count = service.list_assignments()
    return jsonify({"job_assignments": [a.to_dict() for a in assignments], "count": count}), 200 # fmt: skip


# ---------------------------------------------------------------------
# Job Assignment Create API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments", methods=["POST"])
@employee_required
def create_job_assignment():
    """Create a new job assignment from JSON payload."""
    req = CreateJobAssignmentRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = JobAssignmentService(g.db).create_assignment(req)
    return jsonify(response.to_dict()), 201


# ---------------------------------------------------------------------
# Job Assignment Delete API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments/<string:employee_number>", methods=["DELETE"])  # fmt: skip
@employee_required
def delete_job_assignment(employee_number: str):
    """Delete a job assignment."""
    path_req = DeleteJobAssignmentRequest.from_path(employee_number)
    with g.db.begin():
        JobAssignmentService(g.db).delete_assignment(path_req.employee_number)
    return jsonify({"message": "job deleted"}), 200


# ---------------------------------------------------------------------
# Job Assignment Reset API
# ---------------------------------------------------------------------
@job_assignment_bp.route("/job-assignments/reset", methods=["POST"])
@admin_required
def reset_job_assignment():
    """Delete a group of job assignments or all."""
    req = ResetJobAssignmentRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        count = JobAssignmentService(g.db).reset_assignments(req)
    return jsonify({"message": "reset successful", "count": count}), 200
