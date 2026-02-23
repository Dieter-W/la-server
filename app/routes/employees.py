"""Employee CRUD endpoints for job center management."""

from flask import Blueprint, jsonify, request

from app.database import db
from app.models import Employee

employees_bp = Blueprint("employees", __name__)


def _employee_to_dict(emp: Employee) -> dict:
    """Serialize Employee to JSON-serializable dict."""
    return {
        "id": emp.id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "employee_number": emp.employee_number,
        "role": emp.role,
        "active": emp.active,
        "notes": emp.notes,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
    }


def _validate_create_payload(data: dict) -> tuple[bool, str | None]:
    """Validate POST payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object"
    required = ("first_name", "last_name", "employee_number", "role")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"Missing or empty required field: {field}"
    return True, None


def _validate_update_payload(data: dict) -> tuple[bool, str | None]:
    """Validate PUT payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object"
    return True, None


@employees_bp.route("/employees", methods=["GET"])
def list_employees():
    """List employees, optionally filtered by active status."""
    active_param = request.args.get("active")
    query = Employee.query
    if active_param is not None:
        if active_param.lower() in ("true", "1", "yes"):
            query = query.filter(Employee.active == True)
        elif active_param.lower() in ("false", "0", "no"):
            query = query.filter(Employee.active == False)
    employees = query.order_by(Employee.last_name, Employee.first_name).all()
    return jsonify({"employees": [_employee_to_dict(e) for e in employees]})


@employees_bp.route("/employees/<int:employee_id>", methods=["GET"])
def get_employee(employee_id: int):
    """Fetch a single employee by ID."""
    emp = db.session.get(Employee, employee_id)
    if emp is None:
        return jsonify({"error": "Employee not found"}), 404
    return jsonify(_employee_to_dict(emp))


@employees_bp.route("/employees", methods=["POST"])
def create_employee():
    """Create a new employee from JSON payload."""
    data = request.get_json(silent=True)
    valid, err = _validate_create_payload(data)
    if not valid:
        return jsonify({"error": err}), 400
    emp = Employee(
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        employee_number=data["employee_number"].strip(),
        role=data["role"].strip(),
        active=data.get("active", True),
        notes=data.get("notes") or None,
    )
    db.session.add(emp)
    db.session.commit()
    return jsonify(_employee_to_dict(emp)), 201


@employees_bp.route("/employees/<int:employee_id>", methods=["PUT"])
def update_employee(employee_id: int):
    """Update fields of an employee."""
    emp = db.session.get(Employee, employee_id)
    if emp is None:
        return jsonify({"error": "Employee not found"}), 404
    data = request.get_json(silent=True)
    valid, err = _validate_update_payload(data)
    if not valid:
        return jsonify({"error": err}), 400
    updatable = ("first_name", "last_name", "employee_number", "role", "active", "notes")
    for field in updatable:
        if field in data:
            val = data[field]
            if field == "active":
                emp.active = bool(val)
            elif field in ("first_name", "last_name", "employee_number", "role"):
                emp.__setattr__(field, (val or "").strip())
            else:
                emp.__setattr__(field, val if val is not None else None)
    db.session.commit()
    return jsonify(_employee_to_dict(emp))


@employees_bp.route("/employees/<int:employee_id>", methods=["DELETE"])
def delete_employee(employee_id: int):
    """Soft delete (set active=false) or hard delete if ?hard=true."""
    emp = db.session.get(Employee, employee_id)
    if emp is None:
        return jsonify({"error": "Employee not found"}), 404
    hard = request.args.get("hard", "").lower() in ("true", "1", "yes")
    if hard:
        db.session.delete(emp)
        db.session.commit()
        return jsonify({"message": "Employee deleted permanently"}), 200
    emp.active = False
    db.session.commit()
    return jsonify(_employee_to_dict(emp)), 200
