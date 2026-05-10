"""Company CRUD endpoints for job center management."""

from flask import Blueprint, jsonify, request, g

from app.auth.decorations import admin_required
from app.schemas.company import (
    CompanyNameRequest,
    CreateCompanyRequest,
    ListCompaniesQuery,
    UpdateCompanyRequest,
)
from app.services.company import CompanyService

companies_bp = Blueprint("companies", __name__)


# ---------------------------------------------------------------------
# Companies Get-all API
# ---------------------------------------------------------------------
@companies_bp.route("/companies", methods=["GET"])
def list_companies():
    """List companies, optionally filtered by active status."""
    q = ListCompaniesQuery.from_query(request.args)
    with g.db.begin():
        service = CompanyService(g.db)
        companies, count = service.list_companies(q.active)
    return jsonify({"companies": [c.to_dict() for c in companies], "count": count})


# ---------------------------------------------------------------------
# Companies Get API
# ---------------------------------------------------------------------
@companies_bp.route("/companies/<string:company_name>", methods=["GET"])
def get_company(company_name: str):
    """Fetch a single company by name."""
    path_req = CompanyNameRequest.from_path(company_name)
    with g.db.begin():
        response = CompanyService(g.db).get_company(path_req.company_name)
    return jsonify(response.to_dict())


# ---------------------------------------------------------------------
# Companies Create API
# ---------------------------------------------------------------------
@companies_bp.route("/companies", methods=["POST"])
@admin_required
def create_company():
    """Create a new company from JSON payload."""
    req = CreateCompanyRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = CompanyService(g.db).create_company(req)
    return jsonify(response.to_dict()), 201


# ---------------------------------------------------------------------
# Companies Update API
# ---------------------------------------------------------------------
@companies_bp.route("/companies/<string:company_name>", methods=["PUT"])
@admin_required
def update_company(company_name: str):
    """Update fields of a company."""
    path_req = CompanyNameRequest.from_path(company_name)
    req = UpdateCompanyRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = CompanyService(g.db).update_company(path_req.company_name, req)
    return jsonify(response.to_dict())


# ---------------------------------------------------------------------
# Companies Delete API
# ---------------------------------------------------------------------
@companies_bp.route("/companies/<string:company_name>", methods=["DELETE"])
@admin_required
def delete_company(company_name: str):
    """Delete a company."""
    path_req = CompanyNameRequest.from_path(company_name)
    with g.db.begin():
        CompanyService(g.db).delete_company(path_req.company_name)
    return jsonify({"message": "company deleted permanently"}), 200
