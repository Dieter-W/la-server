"""Company jobs max CRUD endpoints for admin maintenance of schedule rows."""

from flask import Blueprint, g, jsonify, request

from app.auth.decorations import admin_required
from app.errors import APIError
from app.schemas.company import CompanyNameRequest
from app.schemas.company_jobs_max import (
    CreateCompanyJobsMaxRequest,
    DeleteCompanyJobsMaxQuery,
    UpdateCompanyJobsMaxRequest,
)
from app.services.company_jobs_max import CompanyJobsMaxService

company_jobs_max_bp = Blueprint("company_jobs_max", __name__)


# ---------------------------------------------------------------------
# Company jobs max — list
# ---------------------------------------------------------------------
@company_jobs_max_bp.route("/company-jobs-max/<string:company_name>", methods=["GET"])
def list_company_jobs_max(company_name: str):
    """List stored schedule rows for one company."""
    path_req = CompanyNameRequest.from_path(company_name)
    if request.args.get("workday") is not None:
        raise APIError("INVALID_PART_TIME_WORKDAY", 400)
    if request.args.get("shift") is not None:
        raise APIError("INVALID_PART_TIME_SHIFT", 400)
    with g.db.begin():
        response = CompanyJobsMaxService(g.db).list_company_jobs_max(
            path_req.company_name
        )
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Company jobs max — create
# ---------------------------------------------------------------------
@company_jobs_max_bp.route("/company-jobs-max/<string:company_name>", methods=["POST"])
@admin_required
def create_company_jobs_max(company_name: str):
    """Create a schedule row from JSON payload."""
    path_req = CompanyNameRequest.from_path(company_name)
    req = CreateCompanyJobsMaxRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = CompanyJobsMaxService(g.db).create_company_jobs_max(
            path_req.company_name, req
        )
    return jsonify(response.to_dict()), 201


# ---------------------------------------------------------------------
# Company jobs max — update
# ---------------------------------------------------------------------
@company_jobs_max_bp.route("/company-jobs-max/<string:company_name>", methods=["PUT"])
@admin_required
def update_company_jobs_max(company_name: str):
    """Update jobs_max/notes for one stored workday + shift row."""
    path_req = CompanyNameRequest.from_path(company_name)
    req = UpdateCompanyJobsMaxRequest.from_dict(request.get_json(silent=True))
    with g.db.begin():
        response = CompanyJobsMaxService(g.db).update_company_jobs_max(
            path_req.company_name, req
        )
    return jsonify(response.to_dict()), 200


# ---------------------------------------------------------------------
# Company jobs max — delete
# ---------------------------------------------------------------------
@company_jobs_max_bp.route(
    "/company-jobs-max/<string:company_name>", methods=["DELETE"]
)
@admin_required
def delete_company_jobs_max(company_name: str):
    """Delete all schedule rows, or one row when ``?workday=&shift=`` is set."""
    path_req = CompanyNameRequest.from_path(company_name)
    q = DeleteCompanyJobsMaxQuery.from_query(request.args)
    with g.db.begin():
        service = CompanyJobsMaxService(g.db)
        if q.workday is None:
            result = service.delete_all_company_jobs_max(path_req.company_name)
        else:
            result = service.delete_one_company_jobs_max(
                path_req.company_name, q.workday, q.shift
            )
    return jsonify(result), 200
