"""Shared validation helpers used across route and service modules."""

from flask import current_app
from stdnum.iso7064 import mod_97_10


# ---------------------------------------------------------------------
# Employee numbers
# ---------------------------------------------------------------------
def validate_employee_number(employee_number: str) -> tuple[bool, str | None]:
    """Validate the ISO 7064 mod-97-10 checksum on an employee number.

    Returns ``(valid, error_message)``. Validation is skipped when the Flask
    app config key ``VALIDATE_CHECK_SUM`` is ``False``.
    """
    if current_app.config.get("VALIDATE_CHECK_SUM", True) and not mod_97_10.is_valid(
        employee_number
    ):
        return False, "EMPLOYEE_NUMBER_WRONG"
    return True, None


# ---------------------------------------------------------------------
# Job assignment numbers
# ---------------------------------------------------------------------
# Assignment number format: ``*`` prefix + 5-digit assignment id + 2 mod 97-10 check digits (ISO 7064).
# Check digits are computed on the id digits only, not on the prefix.
_JOB_ASSIGNMENT_PREFIX = "*"
_JOB_ASSIGNMENT_ID_WIDTH = 5
_JOB_ASSIGNMENT_CHECK_LEN = 2


def create_job_assignment_number(job_assignment_id: int) -> str:
    """Build the API job-assignment number: ``*``, zero-padded id, then check digits.

    ISO 7064 mod 97-10 check digits are computed on the id digits only.
    """
    if job_assignment_id < 0:
        msg = "job_assignment_id must be non-negative"
        raise ValueError(msg)
    payload = f"{job_assignment_id:0{_JOB_ASSIGNMENT_ID_WIDTH}d}"
    return f"{_JOB_ASSIGNMENT_PREFIX}" + payload + mod_97_10.calc_check_digits(payload)


def validate_job_assignment_number(
    job_assignment_number: str,
) -> tuple[bool, str | None, int | None]:
    """Validate checksum and decode the numeric job-assignment id.

    Returns ``(True, None, assignment_id)`` on success, or
    ``(False, "JOB_ASSIGNMENT_NUMBER_WRONG", None)``. Checksum validation covers the
    id digits and their check digits only (the ``*`` prefix is excluded).
    """
    expected_len = (
        len(_JOB_ASSIGNMENT_PREFIX)
        + _JOB_ASSIGNMENT_ID_WIDTH
        + _JOB_ASSIGNMENT_CHECK_LEN
    )
    if len(
        job_assignment_number
    ) != expected_len or not job_assignment_number.startswith(_JOB_ASSIGNMENT_PREFIX):
        return False, "JOB_ASSIGNMENT_NUMBER_WRONG", None

    start = len(_JOB_ASSIGNMENT_PREFIX)
    body = job_assignment_number[start:]
    # ISO 7064 mod 97-10 applies to id + check digits; the literal prefix must be excluded.
    if not mod_97_10.is_valid(body):
        return False, "JOB_ASSIGNMENT_NUMBER_WRONG", None

    assignment_id = int(job_assignment_number[start : start + _JOB_ASSIGNMENT_ID_WIDTH])

    return True, None, assignment_id
