"""Company CRUD endpoints for job center management."""

from flask import Blueprint, jsonify, request

from app.database import db
from app.errors import APIError
from app.models import Company

companies_bp = Blueprint("companies", __name__)


def _company_to_dict(comp: Company) -> dict:
    """Serialize Companye to JSON-serializable dict."""
    return {
        "id": comp.id,
        "company_name": comp.company_name,
        "number_of_jobs": comp.number_of_jobs,
        "pay_per_hour": comp.pay_per_hour,
        "active": comp.active,
        "notes": comp.notes,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
        "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
    }


def _validate_create_payload(data: dict) -> tuple[bool, str | None]:
    """Validate POST payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object"
    required = ("company_name", "number_of_jobs", "pay_per_hour")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"Missing or empty required field: {field}"
    return True, None


def _validate_update_payload(data: dict) -> tuple[bool, str | None]:
    """Validate PUT payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object"
    company_name = data.get("company_name")
    if (
        company_name is not None
        and not Company.query.filter(Company.company_name == company_name).first()
    ):
        return False, "Company not found"
    return True, None


@companies_bp.route("/companies", methods=["GET"])
def list_companies():
    """List companies, optionally filtered by active status."""
    active_param = request.args.get("active")
    with db.session.begin():
        query = Company.query
        if active_param is not None:
            if active_param.lower() in ("true", "1", "yes"):
                query = query.filter(Company.active.is_(True))
            elif active_param.lower() in ("false", "0", "no"):
                query = query.filter(Company.active.is_(False))
        companies = query.order_by(Company.company_name).all()
        return jsonify(
            {
                "companies": [_company_to_dict(e) for e in companies],
                "count": len(companies),
            }
        )


@companies_bp.route("/companies/<string:company_name>", methods=["GET"])
def get_company(company_name: str):
    """Fetch a single company by id."""
    with db.session.begin():
        comp = Company.query.filter(Company.company_name == company_name).first()
        if comp is None:
            raise APIError("Company not found", 404)
        return jsonify(_company_to_dict(comp))


@companies_bp.route("/companies", methods=["POST"])
def create_company():
    """Create a new company from JSON payload."""
    data = request.get_json(silent=True)
    valid, err = _validate_create_payload(data)
    if not valid:
        raise APIError(err, 400)
    with db.session.begin():
        comp = Company(
            company_name=data["company_name"].strip(),
            number_of_jobs=data["number_of_jobs"],
            pay_per_hour=data["pay_per_hour"],
            active=data.get("active", True),
            notes=data.get("notes") or None,
        )
        db.session.add(comp)
        db.session.flush()
        return jsonify(_company_to_dict(comp)), 201


@companies_bp.route("/companies/<string:company_name>", methods=["PUT"])
def update_company(company_name: str):
    """Update fields of a company."""
    data = request.get_json(silent=True)
    valid, err = _validate_update_payload(data)
    if not valid:
        raise APIError(err, 400)
    with db.session.begin():
        comp = Company.query.filter(Company.company_name == company_name).first()
        if comp is None:
            raise APIError("Company not found", 404)
        updatable = (
            "company_name",
            "number_of_jobs",
            "pay_per_hour",
            "active",
            "notes",
        )
        for field in updatable:
            if field in data:
                val = data[field]
                if field == "active":
                    comp.active = bool(val)
                elif field in ("company_name"):
                    comp.__setattr__(field, (val or "").strip())
                elif field in ("number_of_jobs", "pay_per_hour"):
                    comp.__setattr__(field, int(val) if val is not None else None)
                else:
                    comp.__setattr__(field, val if val is not None else None)
        return jsonify(_company_to_dict(comp))


@companies_bp.route("/companies/<string:company_name>", methods=["DELETE"])
def delete_company(company_name: str):
    """Delete a company."""
    with db.session.begin():
        comp = Company.query.filter(Company.company_name == company_name).first()
        if comp is None:
            raise APIError("Company not found", 404)
        db.session.delete(comp)
        return jsonify({"message": "Company deleted permanently"}), 200
