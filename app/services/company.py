"""Business logic for the companies resource."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.errors import APIError
from app.models import Company
from app.repositories.company import CompanyRepository
from app.schemas.company import (
    CompanyResponse,
    CreateCompanyRequest,
    UpdateCompanyRequest,
)
from app.village_config import get_hourly_pay_increase

logger = logging.getLogger(__name__)


class CompanyService:
    def __init__(self, db: Session) -> None:
        """Repository for company aggregates and hourly-pay village bonus."""
        self.repo = CompanyRepository(db)

    # ---------------------------------------------------------------------
    # Companies — list
    # ---------------------------------------------------------------------
    def list_companies(self, active: bool | None) -> tuple[list[CompanyResponse], int]:
        """All companies + job counts; hourly_pay includes village bump."""
        rows = self.repo.list_with_job_counts(active)
        increase = get_hourly_pay_increase()
        responses = [
            CompanyResponse.from_orm(comp, assigned_jobs, increase)
            for comp, assigned_jobs in rows
        ]
        return responses, len(responses)

    # ---------------------------------------------------------------------
    # Companies — get one
    # ---------------------------------------------------------------------
    def get_company(self, company_name: str) -> CompanyResponse:
        """Fetch one company by name or COMPANY_NOT_FOUND."""
        comp = self.repo.get_by_name(company_name)
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)
        assigned_jobs = self.repo.count_assigned_jobs(comp.id)
        return CompanyResponse.from_orm(comp, assigned_jobs, get_hourly_pay_increase())

    # ---------------------------------------------------------------------
    # Companies — create
    # ---------------------------------------------------------------------
    def create_company(self, req: CreateCompanyRequest) -> CompanyResponse:
        """Persist company and return serialized row (0 assigned jobs)."""
        comp = Company(
            company_name=req.company_name,
            jobs_max=req.jobs_max,
            hourly_pay=req.hourly_pay,
            active=req.active,
            notes=req.notes,
        )
        self.repo.save(comp)
        logger.info("Company created id=%s company_name=%s", comp.id, comp.company_name)
        return CompanyResponse.from_orm(comp, 0, get_hourly_pay_increase())

    # ---------------------------------------------------------------------
    # Companies — update
    # ---------------------------------------------------------------------
    def update_company(
        self, company_name: str, req: UpdateCompanyRequest
    ) -> CompanyResponse:
        """Apply partial fields from ``req`` then return fresh aggregate view."""
        comp = self.repo.get_by_name(company_name)
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)

        if "company_name" in req:
            comp.company_name = req.company_name
        if "jobs_max" in req:
            comp.jobs_max = req.jobs_max
        if "hourly_pay" in req:
            comp.hourly_pay = req.hourly_pay
        if "active" in req:
            comp.active = req.active
        if "notes" in req:
            comp.notes = req.notes

        assigned_jobs = self.repo.count_assigned_jobs(comp.id)
        logger.info("Company updated id=%s company_name=%s", comp.id, comp.company_name)
        return CompanyResponse.from_orm(comp, assigned_jobs, get_hourly_pay_increase())

    # ---------------------------------------------------------------------
    # Companies — delete
    # ---------------------------------------------------------------------
    def delete_company(self, company_name: str) -> None:
        """Hard-delete company row if it exists."""
        comp = self.repo.get_by_name(company_name)
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)
        self.repo.delete(comp)
        logger.info("Company deleted id=%s company_name=%s", comp.id, comp.company_name)
