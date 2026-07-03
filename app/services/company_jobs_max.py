"""Business logic for the company-jobs-max resource (CRUD on schedule rows)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.camp_time import CAMP_SHIFTS
from app.errors import APIError
from app.models import Company, CompanyJobsMax
from app.repositories.company import CompanyRepository
from app.repositories.company_jobs_max import CompanyJobsMaxRepository
from app.schemas.company_jobs_max import (
    CompanyJobsMaxRowResponse,
    CreateCompanyJobsMaxRequest,
    ListCompanyJobsMaxResponse,
    UpdateCompanyJobsMaxRequest,
    verify_jobs_max,
)
from app.schemas.part_time import PART_TIME_STORED_WORKDAYS

logger = logging.getLogger(__name__)

_WORKDAY_ORDER = {slug: index for index, slug in enumerate(PART_TIME_STORED_WORKDAYS)}
_SHIFT_ORDER = {slug: index for index, slug in enumerate(CAMP_SHIFTS)}


class CompanyJobsMaxService:
    def __init__(self, db: Session) -> None:
        self.company_repo = CompanyRepository(db)
        self.repo = CompanyJobsMaxRepository(db)

    def _resolve_company(self, company_name: str) -> Company:
        """Load company by name or raise COMPANY_NOT_FOUND."""
        comp = self.company_repo.get_by_name(company_name)
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)
        return comp

    def _sort_rows(self, rows: list[CompanyJobsMax]) -> list[CompanyJobsMax]:
        return sorted(
            rows,
            key=lambda row: (
                _WORKDAY_ORDER.get(row.workday, 999),
                _SHIFT_ORDER.get(row.shift, 999),
            ),
        )

    def list_company_jobs_max(self, company_name: str) -> ListCompanyJobsMaxResponse:
        """Return stored schedule rows ordered by workday then shift."""
        comp = self._resolve_company(company_name)
        rows = self._sort_rows(self.repo.list_by_company_id(comp.id))
        responses = [CompanyJobsMaxRowResponse.from_orm(row) for row in rows]
        return ListCompanyJobsMaxResponse(
            company_name=company_name,
            company_jobs_max=responses,
            count=len(responses),
        )

    def create_company_jobs_max(
        self, company_name: str, req: CreateCompanyJobsMaxRequest
    ) -> CompanyJobsMaxRowResponse:
        """Create one schedule row.

        Uniqueness on ``(company_id, workday, shift)`` is enforced by the database
        constraint ``uq_company_jobs_max_company_workday_shift``; a duplicate surfaces
        as ``409 CONSTRAINT_VIOLATION`` via the global IntegrityError handler.
        """
        comp = self._resolve_company(company_name)
        row = CompanyJobsMax(
            company_id=comp.id,
            workday=req.workday,
            shift=req.shift,
            jobs_max=req.jobs_max,
            notes=req.notes,
        )
        self.repo.save(row)
        logger.info(
            "Company jobs max row created company_name=%s workday=%s shift=%s",
            company_name,
            req.workday,
            req.shift,
        )
        return CompanyJobsMaxRowResponse.from_orm(row)

    def update_company_jobs_max(
        self, company_name: str, req: UpdateCompanyJobsMaxRequest
    ) -> CompanyJobsMaxRowResponse:
        """Partial update by stored workday + shift lookup keys."""
        comp = self._resolve_company(company_name)
        row = self.repo.get_by_company_workday_shift(comp.id, req.workday, req.shift)
        if row is None:
            raise APIError("COMPANY_JOBS_MAX_NOT_FOUND", 404)

        if "jobs_max" in req:
            row.jobs_max = verify_jobs_max(req.jobs_max)
        if "notes" in req:
            row.notes = req.notes

        logger.info(
            "Company jobs max row updated company_name=%s workday=%s shift=%s",
            company_name,
            req.workday,
            req.shift,
        )
        return CompanyJobsMaxRowResponse.from_orm(row)

    def delete_all_company_jobs_max(self, company_name: str) -> dict:
        """Delete all schedule rows (idempotent when none exist)."""
        comp = self._resolve_company(company_name)
        count = self.repo.delete_all_by_company_id(comp.id)
        logger.info(
            "Company jobs max rows deleted company_name=%s count=%s",
            company_name,
            count,
        )
        return {"message": "company jobs max rows deleted", "count": count}

    def delete_one_company_jobs_max(
        self, company_name: str, workday: str, shift: str
    ) -> dict:
        """Delete one schedule row by stored workday + shift slugs."""
        comp = self._resolve_company(company_name)
        row = self.repo.get_by_company_workday_shift(comp.id, workday, shift)
        if row is None:
            raise APIError("COMPANY_JOBS_MAX_NOT_FOUND", 404)
        self.repo.delete(row)
        logger.info(
            "Company jobs max row deleted company_name=%s workday=%s shift=%s",
            company_name,
            workday,
            shift,
        )
        return {"message": "company jobs max row deleted"}
