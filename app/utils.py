"""Shared validation helpers used across route and service modules."""

from flask import current_app
from stdnum.iso7064 import mod_97_10


def validate_checksum(employee_number: str) -> tuple[bool, str | None]:
    """Validate the ISO 7064 mod-97-10 checksum on an employee number.

    Returns ``(valid, error_message)``. Validation is skipped when the Flask
    app config key ``VALIDATE_CHECK_SUM`` is ``False``.
    """
    if current_app.config.get("VALIDATE_CHECK_SUM", True) and not mod_97_10.is_valid(
        employee_number
    ):
        return False, "EMPLOYEE_NUMBER_WRONG"
    return True, None
