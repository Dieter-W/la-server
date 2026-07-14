"""Job assignment history API tests (archive on delete/reset, read-only JSON + CSV)."""

import csv
import io
from dataclasses import fields
from datetime import timezone
from unittest.mock import patch
from urllib.parse import quote

from app.services.job_assignment_history import (
    CSV_BOM,
    CSV_COLUMNS,
    JobAssignmentHistoryService,
)
from app.schemas.job_assignment_history import JobAssignmentHistoryRowResponse
from app.utils import create_job_assignment_number
from app.village_config import get_hourly_pay_increase, get_hourly_pay_tax

from tests.test_camp_time import CAMP_MONDAY
from tests.test_utils import (
    _login_as_admin,
    _login_as_employee,
    _login_as_staff,
)

CAMP_MONDAY_DATE = CAMP_MONDAY.date()
EFFECTIVE_HOURLY_PAY = 9 + get_hourly_pay_increase()
VILLAGE_TAX = get_hourly_pay_tax()

BAUHOF_HISTORY = {
    "employee_number": "P00370",
    "first_name": "Peter",
    "last_name": "Krause",
    "age": 40,
    "company_name": "Bauhof",
    "hourly_pay": EFFECTIVE_HOURLY_PAY,
    "tax": VILLAGE_TAX,
}

BANK_HISTORY = {
    "employee_number": "M00155",
    "first_name": "Max",
    "last_name": "Mustermann",
    "age": 7,
    "company_name": "Bank",
    "hourly_pay": EFFECTIVE_HOURLY_PAY,
    "tax": VILLAGE_TAX,
}


def _history_headers(token: str | None = None) -> dict:
    if token is None:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _delete_bauhof_assignment(client, token: str) -> None:
    job_number = create_job_assignment_number(2)
    response = client.delete(
        f"/api/job-assignments/{job_number}",
        headers=_history_headers(token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200


def _reset_all_assignments(client, token: str) -> None:
    response = client.post(
        "/api/job-assignments/reset",
        headers=_history_headers(token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200


def _reset_company_assignments(client, token: str, company_name: str) -> None:
    response = client.post(
        "/api/job-assignments/reset",
        headers=_history_headers(token),
        json={"company_name": company_name},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200


def _assert_history_snapshot(row: dict, expected: dict, *, end_reason: str) -> None:
    for key, value in expected.items():
        assert row[key] == value
    assert row["end_reason"] == end_reason
    assert row["started_at"] is not None
    assert row["ended_at"] is not None
    assert row["created_at"] is not None
    assert row["started_camp_date"] == row["started_at"][:10]
    assert row["ended_camp_date"] == row["ended_at"][:10]
    assert isinstance(row["minutes_worked"], int)
    assert row["minutes_worked"] >= 0


def _parse_csv_response(response) -> tuple[list[str], list[dict[str, str]]]:
    text = response.data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader.fieldnames or []), list(reader)


# ---------------------------------------------------------------------
# Archive — delete one assignment
# ---------------------------------------------------------------------
def test_job_assignment_history_created_on_delete(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """DELETE archives one row with employee/company snapshot and end_reason=deleted."""
    employee_token = _login_as_employee(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _delete_bauhof_assignment(client, employee_token)

    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["count"] == 1

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    _assert_history_snapshot(data["history"][0], BAUHOF_HISTORY, end_reason="deleted")


# ---------------------------------------------------------------------
# Archive — reset all
# ---------------------------------------------------------------------
def test_job_assignment_history_created_on_reset_all(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Admin reset-all archives every live assignment with end_reason=reset_all."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["count"] == 0

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2

    assert all(row["end_reason"] == "reset_all" for row in data["history"])

    bauhof_rows = [row for row in data["history"] if row["employee_number"] == "P00370"]
    assert len(bauhof_rows) == 1
    _assert_history_snapshot(bauhof_rows[0], BAUHOF_HISTORY, end_reason="reset_all")

    bank_rows = [row for row in data["history"] if row["employee_number"] == "M00155"]
    assert len(bank_rows) == 1
    _assert_history_snapshot(bank_rows[0], BANK_HISTORY, end_reason="reset_all")


# ---------------------------------------------------------------------
# Archive — reset by company
# ---------------------------------------------------------------------
def test_job_assignment_history_created_on_reset_company(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Admin reset scoped to one company archives only that company's assignments."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_company_assignments(client, admin_token, "Bauhof")

    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["count"] == 1

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    _assert_history_snapshot(
        data["history"][0], BAUHOF_HISTORY, end_reason="reset_company"
    )


def test_job_assignment_history_survives_after_live_assignments_removed(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """After reset-all, live assignments are empty but history remains queryable."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["job_assignments"] == []
    assert response.get_json()["count"] == 0

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["count"] == 2


# ---------------------------------------------------------------------
# JSON list — auth
# ---------------------------------------------------------------------
def test_job_assignment_history_list_requires_auth(
    client,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    """GET history without token returns 401."""
    response = client.get("/api/job-assignment-history")
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    assert response.get_json()["error"] == "AUTHORIZATION_REQUIRED"


def test_job_assignment_history_list_forbidden_employee(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """GET history with employee token returns 403."""
    employee_token = _login_as_employee(client, sample_authentication, sample_employee)
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(employee_token),
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    assert response.get_json()["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"


def test_job_assignment_history_list_ok_staff(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Staff token can list archived employment history."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _delete_bauhof_assignment(client, admin_token)

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["count"] == 1


def test_job_assignment_history_list_ok_admin(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Admin token (staff_required) can list archived employment history."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)

    _delete_bauhof_assignment(client, admin_token)

    response = client.get(
        "/api/job-assignment-history",
        headers=_history_headers(admin_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["count"] == 1


# ---------------------------------------------------------------------
# JSON list — filters
# ---------------------------------------------------------------------
def test_job_assignment_history_list_filter_employee_number(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """?employee_number= returns only that participant's archived rows."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    response = client.get(
        "/api/job-assignment-history?employee_number=P00370",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["history"][0]["employee_number"] == "P00370"


def test_job_assignment_history_list_filter_company_name(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """?company_name= returns only rows for that company."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    response = client.get(
        "/api/job-assignment-history?company_name=Bauhof",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["history"][0]["company_name"] == "Bauhof"


def test_job_assignment_history_list_filter_workday(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """?workday= filters on ended_camp_date (same resolver as attendance)."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    camp_monday_utc = CAMP_MONDAY.astimezone(timezone.utc)
    with patch("app.services.job_assignment.utc_now", return_value=camp_monday_utc):
        _reset_all_assignments(client, admin_token)

    response = client.get(
        "/api/job-assignment-history?workday=monday",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == "monday"
    assert data["ended_camp_date"] == CAMP_MONDAY_DATE.isoformat()
    assert data["count"] == 2


def test_job_assignment_history_by_employee_ok(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """GET /job-assignment-history/{employee_number} returns full history for one child."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    response = client.get(
        "/api/job-assignment-history/P00370",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "P00370"
    assert data["count"] == 1
    assert data["history"][0]["company_name"] == "Bauhof"


# ---------------------------------------------------------------------
# JSON list — immutability (no write endpoints)
# ---------------------------------------------------------------------
_WRITE_METHODS = ["POST", "PUT", "PATCH", "DELETE"]


def test_job_assignment_history_no_write_endpoints_list(
    client,
    sample_authentication,
    sample_employee,
):
    """List route rejects POST/PUT/PATCH/DELETE (no successful writes)."""
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)
    headers = _history_headers(staff_token)

    for method in _WRITE_METHODS:
        response = client.open(
            "/api/job-assignment-history",
            method=method,
            headers=headers,
        )
        if response.status_code < 400:
            print(method, response.text)
        assert response.status_code >= 400


def test_job_assignment_history_no_write_endpoints_by_employee(
    client,
    sample_authentication,
    sample_employee,
):
    """Per-participant JSON route rejects POST/PUT/PATCH/DELETE (no successful writes)."""
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)
    headers = _history_headers(staff_token)

    for method in _WRITE_METHODS:
        response = client.open(
            "/api/job-assignment-history/P00370",
            method=method,
            headers=headers,
        )
        if response.status_code < 400:
            print(method, response.text)
        assert response.status_code >= 400


def test_job_assignment_history_no_write_endpoints_export(
    client,
    sample_authentication,
    sample_employee,
):
    """CSV export routes reject POST/PUT/PATCH/DELETE (no successful writes)."""
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)
    headers = _history_headers(staff_token)

    for path in (
        "/api/job-assignment-history/export",
        "/api/job-assignment-history/P00370/export",
    ):
        for method in _WRITE_METHODS:
            response = client.open(path, method=method, headers=headers)
            if response.status_code < 400:
                print(path, method, response.text)
            assert response.status_code >= 400


# ---------------------------------------------------------------------
# CSV export — content-type, BOM, headers, columns
# ---------------------------------------------------------------------
def test_job_assignment_history_export_content_type_and_bom(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """CSV export returns text/csv with UTF-8 BOM and attachment disposition."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _delete_bauhof_assignment(client, admin_token)

    response = client.get(
        "/api/job-assignment-history/export",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.content_type.startswith("text/csv")
    assert response.data.startswith(CSV_BOM.encode("utf-8"))
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "job-assignment-history-all.csv" in response.headers.get(
        "Content-Disposition", ""
    )


def test_job_assignment_history_export_headers_and_columns(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """CSV header row matches stable column order from the service."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _delete_bauhof_assignment(client, admin_token)

    response = client.get(
        "/api/job-assignment-history/export",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    headers, rows = _parse_csv_response(response)
    assert headers == list(CSV_COLUMNS)
    assert len(rows) == 1
    row = rows[0]
    assert row["employee_number"] == "P00370"
    assert row["company_name"] == "Bauhof"
    assert row["end_reason"] == "deleted"
    assert row["hourly_pay"] == str(EFFECTIVE_HOURLY_PAY)
    assert row["tax"] == str(VILLAGE_TAX)
    assert row["started_camp_date"] == row["started_at"][:10]
    assert row["ended_camp_date"] == row["ended_at"][:10]


def test_job_assignment_history_export_row_count(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Filtered CSV export row count matches JSON list count."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _reset_all_assignments(client, admin_token)

    json_response = client.get(
        "/api/job-assignment-history?company_name=Bank",
        headers=_history_headers(staff_token),
    )
    assert json_response.status_code == 200
    json_count = json_response.get_json()["count"]

    csv_response = client.get(
        "/api/job-assignment-history/export?company_name=Bank",
        headers=_history_headers(staff_token),
    )
    assert csv_response.status_code == 200
    _, rows = _parse_csv_response(csv_response)
    assert len(rows) == json_count == 1


def test_job_assignment_history_export_requires_staff(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    """CSV export requires staff or admin token."""
    response = client.get("/api/job-assignment-history/export")
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    assert response.get_json()["error"] == "AUTHORIZATION_REQUIRED"

    employee_token = _login_as_employee(client, sample_authentication, sample_employee)
    response = client.get(
        "/api/job-assignment-history/export",
        headers=_history_headers(employee_token),
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    assert response.get_json()["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"


def test_job_assignment_history_export_by_employee_filename(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Per-participant CSV export uses employee number in attachment filename."""
    admin_token = _login_as_admin(client, sample_authentication, sample_employee)
    staff_token = _login_as_staff(client, sample_authentication, sample_employee)

    _delete_bauhof_assignment(client, admin_token)

    response = client.get(
        "/api/job-assignment-history/P00370/export",
        headers=_history_headers(staff_token),
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert "job-assignment-history-P00370.csv" in response.headers.get(
        "Content-Disposition", ""
    )
    _, rows = _parse_csv_response(response)
    assert len(rows) == 1
    assert rows[0]["employee_number"] == "P00370"


def _sample_history_row(**overrides) -> JobAssignmentHistoryRowResponse:
    data = {
        "employee_number": "P00370",
        "first_name": "Peter",
        "last_name": "Krause",
        "age": 40,
        "company_name": "Bauhof",
        "hourly_pay": EFFECTIVE_HOURLY_PAY,
        "tax": VILLAGE_TAX,
        "started_at": "2026-07-13T10:00:00",
        "started_camp_date": "2026-07-13",
        "ended_at": "2026-07-13T12:00:00",
        "ended_camp_date": "2026-07-13",
        "minutes_worked": 120,
        "end_reason": "deleted",
        "created_at": "2026-07-13T12:00:01",
    }
    data.update(overrides)
    return JobAssignmentHistoryRowResponse(**data)


def _parse_csv_bytes(data: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader.fieldnames or []), list(reader)


def test_job_assignment_history_row_fields_match_csv_columns():
    """Row DTO fields, to_dict keys, and CSV export columns share one definition."""
    field_names = tuple(f.name for f in fields(JobAssignmentHistoryRowResponse))
    assert field_names == tuple(CSV_COLUMNS)

    row = _sample_history_row()
    assert tuple(row.to_dict().keys()) == field_names


def test_build_csv_sanitizes_formula_injection_prefixes():
    """CSV export prefixes formula-trigger cells to prevent Excel formula injection."""
    row = _sample_history_row(
        first_name="=cmd|'/C calc'!A0",
        last_name="\rhidden",
        company_name="@SUM(A1:A9)",
        end_reason="-malicious",
        employee_number="\tP00370",
    )
    _, rows = _parse_csv_bytes(JobAssignmentHistoryService.build_csv([row]))
    assert rows[0]["first_name"] == "'=cmd|'/C calc'!A0"
    assert rows[0]["last_name"] == "'\rhidden"
    assert rows[0]["company_name"] == "'@SUM(A1:A9)"
    assert rows[0]["end_reason"] == "'-malicious"
    assert rows[0]["employee_number"] == "'\tP00370"

    plus_row = _sample_history_row(first_name="+SUM(A1)")
    _, plus_rows = _parse_csv_bytes(JobAssignmentHistoryService.build_csv([plus_row]))
    assert plus_rows[0]["first_name"] == "'+SUM(A1)"


def test_build_csv_leaves_safe_string_cells_unchanged():
    """CSV export does not alter cells that do not start with formula triggers."""
    row = _sample_history_row(
        first_name="Peter",
        last_name="Krause",
        company_name="Bauhof",
        end_reason="deleted",
    )
    _, rows = _parse_csv_bytes(JobAssignmentHistoryService.build_csv([row]))
    assert rows[0]["first_name"] == "Peter"
    assert rows[0]["last_name"] == "Krause"
    assert rows[0]["company_name"] == "Bauhof"
    assert rows[0]["end_reason"] == "deleted"


def test_csv_filename_for_employee_sanitizes_unsafe_characters():
    """Per-participant export filename strips Content-Disposition injection chars."""
    assert (
        JobAssignmentHistoryService.csv_filename_for_employee('P00370"evil\r\n')
        == "job-assignment-history-P00370evil.csv"
    )
    assert (
        JobAssignmentHistoryService.csv_filename_for_employee("P00370")
        == "job-assignment-history-P00370.csv"
    )


def test_csv_filename_for_list_sanitizes_unsafe_characters():
    """List export filename strips unsafe characters from the date suffix."""
    assert (
        JobAssignmentHistoryService.csv_filename_for_list(CAMP_MONDAY_DATE)
        == f"job-assignment-history-{CAMP_MONDAY_DATE.isoformat()}.csv"
    )
    assert (
        JobAssignmentHistoryService.csv_filename_for_list(None)
        == "job-assignment-history-all.csv"
    )


def test_job_assignment_history_export_sanitized_content_disposition(
    client,
    app,
    sample_authentication,
    sample_employee,
):
    """Per-participant CSV export sanitizes employee_number in Content-Disposition."""
    prev = app.config["VALIDATE_CHECK_SUM"]
    app.config["VALIDATE_CHECK_SUM"] = False
    try:
        staff_token = _login_as_staff(client, sample_authentication, sample_employee)
        malicious_number = 'P00370"evil\r\n'
        response = client.get(
            f"/api/job-assignment-history/{quote(malicious_number, safe='')}/export",
            headers=_history_headers(staff_token),
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200

        disposition = response.headers.get("Content-Disposition", "")
        assert (
            disposition
            == 'attachment; filename="job-assignment-history-P00370evil.csv"'
        )
        assert "\r" not in disposition
        assert "\n" not in disposition
    finally:
        app.config["VALIDATE_CHECK_SUM"] = prev
