"""Staff-only read endpoints for job assignment history (append-only audit trail)."""

from flask import Blueprint, Response, g, jsonify, request

from app.auth.decorations import staff_required
from app.schemas.employee import EmployeeNumberRequest
from app.schemas.job_assignment_history import (
    JobAssignmentHistoryWorkdayQuery,
    ListJobAssignmentHistoryQuery,
)
from app.services.job_assignment_history import JobAssignmentHistoryService

job_assignment_history_bp = Blueprint("job_assignment_history", __name__)


def _csv_response(data: bytes, filename: str) -> Response:
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------
# Job assignment history — list
# ---------------------------------------------------------------------
@job_assignment_history_bp.route("/job-assignment-history", methods=["GET"])
@staff_required
def list_job_assignment_history():
    """List archived employment snapshots with optional filters."""
    query = ListJobAssignmentHistoryQuery.from_query(request.args)
    with g.db.begin():
        response = JobAssignmentHistoryService(g.db).list_history(query)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Job assignment history — CSV export (list)
# ---------------------------------------------------------------------
@job_assignment_history_bp.route("/job-assignment-history/export", methods=["GET"])
@staff_required
def export_job_assignment_history():
    """Download filtered history as CSV (UTF-8 with BOM for Excel)."""
    query = ListJobAssignmentHistoryQuery.from_query(request.args)
    with g.db.begin():
        csv_bytes, filename = JobAssignmentHistoryService(g.db).export_history_csv(
            query
        )
    return _csv_response(csv_bytes, filename)


# ---------------------------------------------------------------------
# Job assignment history — per-participant CSV export
# ---------------------------------------------------------------------
@job_assignment_history_bp.route(
    "/job-assignment-history/<string:employee_number>/export", methods=["GET"]
)
@staff_required
def export_job_assignment_history_by_employee(employee_number: str):
    """Download one participant's employment history as CSV."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    query = JobAssignmentHistoryWorkdayQuery.from_query(request.args)
    with g.db.begin():
        csv_bytes, filename = JobAssignmentHistoryService(
            g.db
        ).export_history_by_employee_csv(path_req.employee_number, query)
    return _csv_response(csv_bytes, filename)


# ---------------------------------------------------------------------
# Job assignment history — per participant
# ---------------------------------------------------------------------
@job_assignment_history_bp.route(
    "/job-assignment-history/<string:employee_number>", methods=["GET"]
)
@staff_required
def list_job_assignment_history_by_employee(employee_number: str):
    """Full employment history for one participant."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    query = JobAssignmentHistoryWorkdayQuery.from_query(request.args)
    with g.db.begin():
        response = JobAssignmentHistoryService(g.db).list_history_by_employee(
            path_req.employee_number,
            query,
        )
    return jsonify(response.to_dict()), 200
