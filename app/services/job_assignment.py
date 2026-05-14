"""Business logic for the job_assignments resource."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.errors import APIError
from app.models import JobAssignment
from app.repositories.company import CompanyRepository
from app.repositories.employee import EmployeeRepository
from app.repositories.job_assignment import JobAssignmentRepository
from app.schemas.job_assignment import (
    CreateJobAssignmentRequest,
    JobAssignmentResponse,
    ResetJobAssignmentRequest,
)

logger = logging.getLogger(__name__)


class JobAssignmentService:
    def __init__(self, db: Session) -> None:
        """Repos for assignments, locking company picks, employee lookup."""
        self.repo = JobAssignmentRepository(db)
        self.company_repo = CompanyRepository(db)
        self.employee_repo = EmployeeRepository(db)

    # ---------------------------------------------------------------------
    # Job assignments — list
    # ---------------------------------------------------------------------
    def list_assignments(self) -> tuple[list[JobAssignmentResponse], int]:
        """All assignments ordered by employee repository default."""
        jobs = self.repo.list_all()
        responses = [JobAssignmentResponse.from_orm(j) for j in jobs]
        return responses, len(responses)

    # ---------------------------------------------------------------------
    # Job assignments — create
    # ---------------------------------------------------------------------
    def create_assignment(
        self, req: CreateJobAssignmentRequest
    ) -> JobAssignmentResponse:
        """Assign employee to company under capacity and one-job-per-employee rules."""
        comp = self.company_repo.get_by_name_with_lock(req.company_name)
        if comp is None:
            raise APIError("COMPANY_NOT_FOUND", 404)
        if comp.active is False:
            raise APIError("COMPANY_NOT_ACTIVE", 400)

        result = self.employee_repo.get_with_company(req.employee_number)
        if result is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        emp, _ = result
        if emp.active is False:
            raise APIError("EMPLOYEE_NOT_ACTIVE", 400)

        if self.repo.get_by_employee_id(emp.id) is not None:
            raise APIError("JOB_ALREADY_ASSIGNED", 400)

        assigned_count = self.repo.count_by_company_id(comp.id)
        if assigned_count >= comp.jobs_max:
            raise APIError("NO_JOB_LEFT", 400)

        job = JobAssignment(company_id=comp.id, employee_id=emp.id)
        self.repo.save(job)
        # codeql[py/clear-text-logging-sensitive-data]
        logger.debug(
            "Job assignment created id=%s company_id=%s employee_id=%s",
            job.id,
            job.company_id,
            job.employee_id,
        )
        return JobAssignmentResponse.from_orm(job)

    # ---------------------------------------------------------------------
    # Job assignments — delete one
    # ---------------------------------------------------------------------
    def delete_assignment(self, job_assignment_id: int) -> None:
        """Drop one assignment row by primary key."""
        job = self.repo.get_by_id(job_assignment_id)
        if job is None:
            raise APIError("JOB_ASSIGNMENT_NOT_FOUND", 404)

        emp = job.employees
        employee_number = emp.employee_number if emp is not None else None

        self.repo.delete(job)
        logger.debug(
            "Job assignment deleted id=%s employee_id=%s employee_number=%s",
            job.id,
            job.employee_id,
            employee_number,
        )

    # ---------------------------------------------------------------------
    # Job assignments — reset (bulk)
    # ---------------------------------------------------------------------
    def reset_assignments(self, req: ResetJobAssignmentRequest) -> int:
        """Bulk delete for one company or all; returns deleted row count."""
        if req.company_name:
            comp = self.company_repo.get_by_name(req.company_name)
            if comp is None:
                raise APIError("COMPANY_NOT_FOUND", 404)
            count = self.repo.delete_by_company_id(comp.id)
        else:
            count = self.repo.delete_all()

        logger.warning(
            "Job assignments reset count=%s company_name=%s",
            count,
            req.company_name or "*",
        )
        return count
