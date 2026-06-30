"""Check-in / check-out attendance endpoints."""

from flask import Blueprint, g, jsonify, request

from app.auth.decorations import staff_required
from app.errors import APIError
from app.schemas.attendance import AttendanceWorkdayQuery
from app.schemas.employee import EmployeeNumberRequest
from app.services.attendance import AttendanceService

attendance_bp = Blueprint("attendance", __name__)


def _reject_request_body() -> None:
    """POST check-in/out accept no body; timestamps are server-only."""
    if request.get_data():
        raise APIError("REQUEST_BODY_NOT_ALLOWED", 400)


# ---------------------------------------------------------------------
# Check-in API
# ---------------------------------------------------------------------
@attendance_bp.route("/attendance/check-in/<string:employee_number>", methods=["POST"])
@staff_required
def check_in(employee_number: str):
    """Record check-in for camp today (staff scan at gate)."""
    _reject_request_body()
    path_req = EmployeeNumberRequest.from_path(employee_number)
    with g.db.begin():
        response = AttendanceService(g.db).check_in(path_req.employee_number)
    return jsonify(response.to_dict()), 201


# ---------------------------------------------------------------------
# Check-out API
# ---------------------------------------------------------------------
@attendance_bp.route("/attendance/check-out/<string:employee_number>", methods=["POST"])
@staff_required
def check_out(employee_number: str):
    """Record optional check-out on today's attendance row."""
    _reject_request_body()
    path_req = EmployeeNumberRequest.from_path(employee_number)
    with g.db.begin():
        response = AttendanceService(g.db).check_out(path_req.employee_number)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Check-ins list API
# ---------------------------------------------------------------------
@attendance_bp.route("/attendance/check-ins", methods=["GET"])
def list_check_ins():
    """List all check-ins for a camp day (default today)."""
    workday = request.args.get("workday")
    with g.db.begin():
        response = AttendanceService(g.db).list_check_ins(workday)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Check-outs list API
# ---------------------------------------------------------------------
@attendance_bp.route("/attendance/check-outs", methods=["GET"])
def list_check_outs():
    """List optional check-outs for a camp day (default today)."""
    workday = request.args.get("workday")
    with g.db.begin():
        response = AttendanceService(g.db).list_check_outs(workday)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Per-person attendance history API
# ---------------------------------------------------------------------
@attendance_bp.route("/attendance/<string:employee_number>", methods=["GET"])
def list_attendance(employee_number: str):
    """Full attendance history or one camp day when ``?workday=`` is set."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    query = AttendanceWorkdayQuery.from_query(request.args)
    with g.db.begin():
        response = AttendanceService(g.db).list_attendance(
            path_req.employee_number,
            query,
        )
    return jsonify(response.to_dict()), 200
