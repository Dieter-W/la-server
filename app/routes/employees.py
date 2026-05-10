"""CRUD for camp participants (children and staff); URLs and JSON use *employee* / employee_number as stable API names."""

from flask import Blueprint, jsonify, request, g

from app.auth.decorations import admin_required
from app.schemas.employee import (
    CreateEmployeeRequest,
    DeleteEmployeeQuery,
    EmployeeNumberRequest,
    ListEmployeesQuery,
    UpdateEmployeeRequest,
)
from app.services.employee import EmployeeService

employees_bp = Blueprint("employees", __name__)


# ---------------------------------------------------------------------
# Employees Get-all API
# ---------------------------------------------------------------------
@employees_bp.route("/employees", methods=["GET"])
def list_employees():
    """List employees, optionally filtered by active status."""
    q = ListEmployeesQuery.from_query(request.args)
    with g.db.begin():
        service = EmployeeService(g.db)
        employees, count = service.list_employees(q.active)
    return jsonify({"employees": [e.to_dict() for e in employees], "count": count}), 200


# ---------------------------------------------------------------------
# Employees Get API
# ---------------------------------------------------------------------
@employees_bp.route("/employees/<string:employee_number>", methods=["GET"])
def get_employee(employee_number: str):
    """Fetch a single employee by employee number."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    with g.db.begin():
        response = EmployeeService(g.db).get_employee(path_req.employee_number)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Employees Create API
# ---------------------------------------------------------------------
@employees_bp.route("/employees", methods=["POST"])
@admin_required
def create_employee():
    """Create a new employee from JSON payload."""
    req = CreateEmployeeRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = EmployeeService(g.db).create_employee(req)
    return jsonify(response.to_dict()), 201


# ---------------------------------------------------------------------
# Employees Update API
# ---------------------------------------------------------------------
@employees_bp.route("/employees/<string:employee_number>", methods=["PUT"])
@admin_required
def update_employee(employee_number: str):
    """Update fields of an employee."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    req = UpdateEmployeeRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = EmployeeService(g.db).update_employee(path_req.employee_number, req)
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Employees Delete API
# ---------------------------------------------------------------------
@employees_bp.route("/employees/<string:employee_number>", methods=["DELETE"])
@admin_required
def delete_employee(employee_number: str):
    """Soft delete (set active=false) or hard delete if ?hard=true."""
    path_req = EmployeeNumberRequest.from_path(employee_number)
    opts = DeleteEmployeeQuery.from_query(request.args)
    with g.db.begin():
        service = EmployeeService(g.db)
        if not opts.hard:
            response = service.deactivate_employee(path_req.employee_number)
            return jsonify(response.to_dict()), 200
        else:
            service.hard_delete_employee(path_req.employee_number)
            return jsonify({"message": "employee deleted permanently"}), 200
