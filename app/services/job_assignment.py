"""Business logic for the job_assignments resource."""

from __future__ import annotations

import logging
from datetime import timezone

from sqlalchemy.orm import Session

from app.errors import APIError
from app.models import Employee, JobAssignment, JobAssignmentHistory, utc_now
from app.repositories.attendance import AttendanceRepository
from app.repositories.company import CompanyRepository
from app.repositories.employee import EmployeeRepository
from app.repositories.job_assignment import JobAssignmentRepository
from app.repositories.job_assignment_history import JobAssignmentHistoryRepository
import app.camp_time as camp_time
from app.village_config import get_hourly_pay_increase, get_hourly_pay_tax
from app.schemas.attendance import participant_requires_attendance
from app.schemas.company_jobs_max import effective_jobs_max
from app.schemas.job_assignment import (
    CreateJobAssignmentRequest,
    JobAssignmentEndReason,
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
        self.history_repo = JobAssignmentHistoryRepository(db)

    def _require_today_checkin(self, emp: Employee) -> None:
        """Reject job create/delete when attendance is required but missing for camp today."""
        if participant_requires_attendance(emp):
            if not self.attendance_repo.has_checkin_for_date(
                emp.id, camp_time.camp_today()
            ):
                raise APIError("ATTENDANCE_CHECK_IN_REQUIRED", 400)

    def _archive_assignment(
        self,
        job: JobAssignment,
        *,
        end_reason: JobAssignmentEndReason,
        hourly_pay_increase: int | None = None,
        tax: int | None = None,
    ) -> None:
        """Persist a denormalized snapshot before the live assignment row is removed."""
        employee = job.employees
        company = job.companies
        if employee is None or company is None:
            raise APIError("JOB_ASSIGNMENT_NOT_FOUND", 404)

        if hourly_pay_increase is None:
            hourly_pay_increase = get_hourly_pay_increase()
        if tax is None:
            tax = get_hourly_pay_tax()

        started_at = job.created_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        ended_at = utc_now()
        started_camp_date = camp_time.camp_instant(now=started_at).date()
        ended_camp_date = camp_time.camp_instant(now=ended_at).date()
        minutes_worked = int((ended_at - started_at).total_seconds() // 60)

        record = JobAssignmentHistory(
            started_at=started_at,
            started_camp_date=started_camp_date,
            ended_at=ended_at,
            ended_camp_date=ended_camp_date,
            minutes_worked=minutes_worked,
            end_reason=end_reason,
            employee_number=employee.employee_number,
            first_name=employee.first_name,
            last_name=employee.last_name,
            age=employee.age,
            company_name=company.company_name,
            hourly_pay=company.hourly_pay + hourly_pay_increase,
            tax=tax,
        )
        self.history_repo.insert(record)

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

        self._archive_assignment(job, end_reason=JobAssignmentEndReason.DELETED)

        if not self.repo.delete_by_id(job_assignment_id):
            raise APIError("JOB_ASSIGNMENT_NOT_FOUND", 404)

        logger.debug(
            "Job assignment deleted id=%s employee_id=%s employee_number=%s",
            job_assignment_id,
            employee_id,
            employee_number,
        )

    def delete_assignment_by_employee_number(self, employee_number: str) -> None:
        """Drop the assignment for one employee (staff fallback when timecard is lost)."""
        emp = self.employee_repo.get_by_number(employee_number)
        if emp is None:
            raise APIError("EMPLOYEE_NOT_FOUND", 404)
        job = self.repo.get_by_employee_id(emp.id)
        if job is None:
            raise APIError("JOB_ASSIGNMENT_NOT_FOUND", 404)
        self.delete_assignment(job.id)

    # ---------------------------------------------------------------------
    # Job assignments — reset (bulk)
    # ---------------------------------------------------------------------
    def reset_assignments(self, req: ResetJobAssignmentRequest) -> int:
        """Bulk delete for one company or all; archives each row first."""
        hourly_pay_increase = get_hourly_pay_increase()
        tax = get_hourly_pay_tax()

        if req.company_name:
            comp = self.company_repo.get_by_name(req.company_name)
            if comp is None:
                raise APIError("COMPANY_NOT_FOUND", 404)
            jobs = self.repo.list_all_with_relations(company_id=comp.id)
            end_reason = JobAssignmentEndReason.RESET_COMPANY
            for job in jobs:
                self._archive_assignment(
                    job,
                    end_reason=end_reason,
                    hourly_pay_increase=hourly_pay_increase,
                    tax=tax,
                )
            count = self.repo.delete_by_company_id(comp.id)
        else:
            jobs = self.repo.list_all_with_relations()
            end_reason = JobAssignmentEndReason.RESET_ALL
            for job in jobs:
                self._archive_assignment(
                    job,
                    end_reason=end_reason,
                    hourly_pay_increase=hourly_pay_increase,
                    tax=tax,
                )
            count = self.repo.delete_all()

        logger.warning(
            "Job assignments reset count=%s company_name=%s",
            count,
            req.company_name or "*",
        )
        return count
