"""Part-time CRUD endpoints for admin maintenance of stored schedule rows."""

from flask import Blueprint, g, jsonify, request

from app.auth.decorations import admin_required
from app.errors import APIError
from app.schemas.employee import EmployeeNumberRequest
from app.schemas.part_time import (
    CreatePartTimeRequest,
    DeletePartTimeQuery,
    UpdatePartTimeRequest,
)
from app.services.part_time import PartTimeService

part_time_bp = Blueprint("part_time", __name__)


# ---------------------------------------------------------------------
# Part-time List API
# ---------------------------------------------------------------------
@part_time_bp.route("/part-time/<string:employee_number>", methods=["GET"])
def list_part_times(employee_number: str):
    """List stored part-time rows for one employee."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    if request.args.get("workday") is not None:
        raise APIError("INVALID_PART_TIME_WORKDAY", 400)
    with g.db.begin():
        response = PartTimeService(g.db).list_part_times(path_req.employee_number)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Part-time Create API
# ---------------------------------------------------------------------
@part_time_bp.route("/part-time/<string:employee_number>", methods=["POST"])
@admin_required
def create_part_time(employee_number: str):
    """Create a part-time row from JSON payload."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    req = CreatePartTimeRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = PartTimeService(g.db).create_part_time(path_req.employee_number, req)
    return jsonify(response.to_dict()), 201


# ---------------------------------------------------------------------
# Part-time Update API
# ---------------------------------------------------------------------
@part_time_bp.route("/part-time/<string:employee_number>", methods=["PUT"])
@admin_required
def update_part_time(employee_number: str):
    """Update shift/notes for one stored workday row."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    req = UpdatePartTimeRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = PartTimeService(g.db).update_part_time(path_req.employee_number, req)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Part-time Delete API
# ---------------------------------------------------------------------
@part_time_bp.route("/part-time/<string:employee_number>", methods=["DELETE"])
@admin_required
def delete_part_time(employee_number: str):
    """Delete all part-time rows, or one row when ``?workday=`` is set."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    q = DeletePartTimeQuery.from_query(request.args)
    with g.db.begin():
        service = PartTimeService(g.db)
        if q.workday is None:
            result = service.delete_all_part_times(path_req.employee_number)
        else:
            result = service.delete_one_part_time(path_req.employee_number, q.workday)
    return jsonify(result), 200
