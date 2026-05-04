"""CRUD for camp participants (children and staff); URLs and JSON use *employee* / employee_number as stable API names."""

import logging

from flask import Blueprint, jsonify, request, g
from sqlalchemy import func, distinct

from app.auth.decorations import admin_required
from app.auth.utils import hash_password, verify_access_group
from app.errors import APIError
from app.models import Authentication, Company, Employee, JobAssignment
from app.utils import employee_to_dict, validate_checksum

employees_bp = Blueprint("employees", __name__)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def _validate_create_payload(data: dict) -> tuple[bool, str | None]:
    """Validate POST payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("first_name", "last_name", "employee_number", "role", "auth_group")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    valid, err = validate_checksum(data.get("employee_number"))
    if not valid:
        return False, (f"{err}_IN_JSON")

    valid, err = verify_access_group(data.get("auth_group").strip().lower())
    if not valid:
        return False, (f"{err}_IN_JSON")

    return True, None


def _validate_update_payload(data: dict) -> tuple[bool, str | None]:
    """Validate PUT payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    if data.get("employee_number") is not None:
        valid, err = validate_checksum(data.get("employee_number"))
        if not valid:
            return False, (f"{err}_IN_JSON")

    return True, None


# ---------------------------------------------------------------------
# Employees  Get-all API
# ---------------------------------------------------------------------
@employees_bp.route("/employees", methods=["GET"])
def list_employees():
    """List employees, optionally filtered by active status."""
    active_param = request.args.get("active")

    with g.db.begin():
        emp = (
            g.db.query(Employee, Company.company_name.label("company_name"))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .order_by(Employee.employee_number)
        )

        if active_param is not None:
            if active_param.lower() in ("true", "1", "yes"):
                emp = emp.filter(Employee.active.is_(True))
            elif active_param.lower() in ("false", "0", "no"):
                emp = emp.filter(Employee.active.is_(False))

        emp_entries = emp.with_entities(func.count(distinct(Employee.id))).scalar()

        return (
            jsonify(
                {
                    "employees": [
                        employee_to_dict(e, company_name)
                        for e, company_name in emp.all()
                    ],
                    "count": emp_entries,
                }
            ),
            200,
        )


# ---------------------------------------------------------------------
# Employees Get API
# ---------------------------------------------------------------------
@employees_bp.route("/employees/<string:employee_number>", methods=["GET"])
def get_employee(employee_number: str):
    """Fetch a single employee by employee number."""
    valid, err = validate_checksum(employee_number)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        emp_comp = (
            g.db.query(Employee, Company.company_name.label("company_name"))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if emp_comp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        emp, company_name = emp_comp

        return jsonify(employee_to_dict(emp, company_name)), 200


# ---------------------------------------------------------------------
# Employees Create API
# ---------------------------------------------------------------------
@employees_bp.route("/employees", methods=["POST"])
@admin_required
def create_employee():
    """Create a new employee from JSON payload."""
    data = request.get_json(silent=True)
    valid, err = _validate_create_payload(data)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        emp = Employee(
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            employee_number=data["employee_number"].strip(),
            role=data["role"].strip(),
            active=data.get("active", True),
            notes=data.get("notes") or None,
            authentication=Authentication(
                auth_group=data["auth_group"].strip().lower(),
                password_must_change=True,
                password_hash=hash_password(data["last_name"].strip()),
            ),
        )

        g.db.add(emp)
        g.db.flush()
        # codeql[py/clear-text-logging-sensitive-data]
        logger.info(
            "Employee created id=%s employee_number=%s",
            emp.id,
            emp.employee_number,
        )
        return (
            jsonify(
                {
                    **employee_to_dict(emp, ""),
                    "auth_group": emp.authentication.auth_group,
                }
            ),
            201,
        )


# ---------------------------------------------------------------------
# Employees Update API
# ---------------------------------------------------------------------
@employees_bp.route("/employees/<string:employee_number>", methods=["PUT"])
@admin_required
def update_employee(employee_number: str):
    """Update fields of an employee."""
    valid, err = validate_checksum(employee_number)
    if not valid:
        raise APIError(err, 400)

    data = request.get_json(silent=True)
    valid, err = _validate_update_payload(data)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        emp_comp = (
            g.db.query(Employee, Company.company_name.label("company_name"))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if emp_comp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        emp, company_name = emp_comp

        updatable = (
            "first_name",
            "last_name",
            "employee_number",
            "role",
            "active",
            "notes",
        )

        for field in updatable:
            if field in data:
                val = data[field]
                if field == "active":
                    emp.active = bool(val)
                elif field in ("first_name", "last_name", "employee_number", "role"):
                    emp.__setattr__(field, (val or "").strip())
                else:
                    emp.__setattr__(field, val if val is not None else None)

        # codeql[py/clear-text-logging-sensitive-data]
        logger.info(
            "Employee updated id=%s employee_number=%s", emp.id, emp.employee_number
        )
        return jsonify(employee_to_dict(emp, company_name)), 200


# ---------------------------------------------------------------------
# Employees Delete API
# ---------------------------------------------------------------------
@employees_bp.route("/employees/<string:employee_number>", methods=["DELETE"])
@admin_required
def delete_employee(employee_number: str):
    """Soft delete (set active=false) or hard delete if ?hard=true."""
    valid, err = validate_checksum(employee_number)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        emp_comp = (
            g.db.query(Employee, Company.company_name.label("company_name"))
            .outerjoin(Employee.job_assignments)
            .outerjoin(JobAssignment.companies)
            .filter(Employee.employee_number == employee_number)
            .first()
        )
        if emp_comp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)

        emp, company_name = emp_comp

        hard = request.args.get("hard", "").lower() in ("true", "1", "yes")
        if not hard:
            emp.active = False
            # codeql[py/clear-text-logging-sensitive-data]
            logger.info(
                "Employee deactivated id=%s employee_number=%s",
                emp.id,
                emp.employee_number,
            )
            return jsonify(employee_to_dict(emp, company_name)), 200
        else:
            g.db.delete(emp)
            # codeql[py/clear-text-logging-sensitive-data]
            logger.info(
                "Employee deleted hard id=%s employee_number=%s",
                emp.id,
                employee_number,
            )
            return jsonify({"message": "employee deleted permanently"}), 200
