"""Business logic for the job_assignments resource."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.errors import APIError
from app.models import Employee, JobAssignment
from app.repositories.attendance import AttendanceRepository
from app.repositories.company import CompanyRepository
from app.repositories.employee import EmployeeRepository
from app.repositories.job_assignment import JobAssignmentRepository
import app.camp_time as camp_time
from app.schemas.attendance import participant_requires_attendance
from app.schemas.company_jobs_max import effective_jobs_max
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
        self.attendance_repo = AttendanceRepository(db)

    def _require_today_checkin(self, emp: Employee) -> None:
        """Reject job create/delete when attendance is required but missing for camp today."""
        if participant_requires_attendance(emp):
            if not self.attendance_repo.has_checkin_for_date(
                emp.id, camp_time.camp_today()
            ):
                raise APIError("ATTENDANCE_CHECK_IN_REQUIRED", 400)

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

        self._require_today_checkin(emp)

        if self.repo.get_by_employee_id(emp.id) is not None:
            raise APIError("JOB_ALREADY_ASSIGNED", 400)

        assigned_count = self.repo.count_by_company_id(comp.id)
        if assigned_count >= effective_jobs_max(comp):
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
        """Drop one assignment row by primary key (idempotent under concurrency)."""
        job = self.repo.get_by_id(job_assignment_id)
        if job is None:
            raise APIError("JOB_ASSIGNMENT_NOT_FOUND", 404)

        # The check-in gate intentionally keys on the assignment's own employee
        # (the job owner), not the requesting/authenticated user. This mirrors
        # create_assignment, which gates on the employee being assigned, so a
        # job can only be created or removed while its owner is checked in.
        if job.employees is not None:
            self._require_today_checkin(job.employees)

        employee_id = job.employee_id
        employee_number = (
            job.employees.employee_number if job.employees is not None else None
        )

        if not self.repo.delete_by_id(job_assignment_id):
            raise APIError("JOB_ASSIGNMENT_NOT_FOUND", 404)

        logger.debug(
            "Job assignment deleted id=%s employee_id=%s employee_number=%s",
            job_assignment_id,
            employee_id,
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
