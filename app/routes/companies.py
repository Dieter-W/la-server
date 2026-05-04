"""Company CRUD endpoints for job center management."""

import logging

from flask import Blueprint, jsonify, request, g
from sqlalchemy import func

from app.errors import APIError
from app.models import Company, JobAssignment

from app.auth.decorations import admin_required

companies_bp = Blueprint("companies", __name__)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def _company_to_dict(comp: Company, assigned_jobs) -> dict:
    """Serialize Company to JSON-serializable dict."""
    return {
        "id": comp.id,
        "company_name": comp.company_name,
        "jobs": {
            "available": comp.jobs_max - assigned_jobs,
            "max": comp.jobs_max,
        },
        "pay_per_hour": comp.pay_per_hour,
        "active": comp.active,
        "notes": comp.notes,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
        "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
    }


def _validate_create_payload(data: dict) -> tuple[bool, str | None]:
    """Validate POST payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    required = ("company_name", "jobs_max", "pay_per_hour")
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

    return True, None


def _validate_update_payload(data: dict) -> tuple[bool, str | None]:
    """Validate PUT payload. Returns (valid, error_message)."""
    if not data or not isinstance(data, dict):
        return False, "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

    return True, None


# ---------------------------------------------------------------------
# Companies Get-all API
# ---------------------------------------------------------------------
@companies_bp.route("/companies", methods=["GET"])
def list_companies():
    """List companies, optionally filtered by active status."""
    active_param = request.args.get("active")

    with g.db.begin():
        comp = (
            g.db.query(Company, func.count(JobAssignment.id).label("assigned_jobs"))
            .outerjoin(JobAssignment)
            .group_by(Company.id)
            .order_by(Company.company_name)
        )

        if active_param is not None:
            if active_param.lower() in ("true", "1", "yes"):
                comp = comp.filter(Company.active.is_(True))
            elif active_param.lower() in ("false", "0", "no"):
                comp = comp.filter(Company.active.is_(False))

        comp_entries = comp.count()

        return jsonify(
            {
                "companies": [
                    _company_to_dict(e, assigned_jobs) for e, assigned_jobs in (comp)
                ],
                "count": comp_entries,
            }
        )


@companies_bp.route("/companies/<string:company_name>", methods=["GET"])
def get_company(company_name: str):
    """Fetch a single company by id."""
    with g.db.begin():
        comp = g.db.query(Company).filter(Company.company_name == company_name).first()
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)

        jobs_assigned = (
            g.db.query(JobAssignment)
            .filter(JobAssignment.company_id == comp.id)
            .count()
        )

        return jsonify(_company_to_dict(comp, jobs_assigned))


@companies_bp.route("/companies", methods=["POST"])
@admin_required
def create_company():
    """Create a new company from JSON payload."""
    data = request.get_json(silent=True)
    valid, err = _validate_create_payload(data)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        comp = Company(
            company_name=data["company_name"].strip(),
            jobs_max=data["jobs_max"],
            pay_per_hour=data["pay_per_hour"],
            active=data.get("active", True),
            notes=data.get("notes") or None,
        )

        jobs_assigned = 0

        g.db.add(comp)
        g.db.flush()
        logger.info("Company created id=%s company_name=%s", comp.id, comp.company_name)
        return jsonify(_company_to_dict(comp, jobs_assigned)), 201


@companies_bp.route("/companies/<string:company_name>", methods=["PUT"])
@admin_required
def update_company(company_name: str):
    """Update fields of a company."""
    data = request.get_json(silent=True)
    valid, err = _validate_update_payload(data)
    if not valid:
        raise APIError(err, 400)

    with g.db.begin():
        comp = g.db.query(Company).filter(Company.company_name == company_name).first()
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)
        updatable = (
            "company_name",
            "jobs_max",
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
                elif field in ("jobs_max", "pay_per_hour"):
                    comp.__setattr__(field, int(val) if val is not None else None)
                else:
                    comp.__setattr__(field, val if val is not None else None)

        jobs_assigned = (
            g.db.query(JobAssignment)
            .filter(JobAssignment.company_id == comp.id)
            .count()
        )

        logger.info("Company updated id=%s company_name=%s", comp.id, comp.company_name)
        return jsonify(_company_to_dict(comp, jobs_assigned))


@companies_bp.route("/companies/<string:company_name>", methods=["DELETE"])
@admin_required
def delete_company(company_name: str):
    """Delete a company."""
    with g.db.begin():
        comp = g.db.query(Company).filter(Company.company_name == company_name).first()
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)

        g.db.delete(comp)
        logger.info("Company deleted id=%s company_name=%s", comp.id, comp.company_name)
        return jsonify({"message": "company deleted permanently"}), 200
