"""Shared serialization's and validation helpers used across route modules."""

from flask import current_app
from stdnum.iso7064 import mod_97_10

from app.models import Employee


def employee_to_dict(
    emp: Employee, company_name: str | None, auth_group: str | None = None
) -> dict:
    """Serialize an Employee row to a JSON-safe dict.

    Pass ``auth_group`` to include the authentication group in the response
    (used by auth routes); omit it for plain employee endpoints.
    """
    result = {
        "id": emp.id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "employee_number": emp.employee_number,
        "role": emp.role,
        "company": company_name or "",
        "active": emp.active,
        "notes": emp.notes,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
    }
    if auth_group is not None:
        result["auth_group"] = auth_group
    return result


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
