"""Part-time CRUD API tests (``/api/part-time``)."""

import pytest

from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    PART_TIME_STORED_WORKDAYS,
    WEEKDAYS_WORKDAY,
)
from tests.test_utils import _login_as_admin, _login_as_employee, _login_as_staff

payload_create = {
    "workday": "wednesday",
    "shift": "morning",
    "notes": "Camp day",
}

payload_create_default_shift = {
    "workday": "friday",
}

payload_create_aggregate = {
    "workday": WEEKDAYS_WORKDAY,
    "shift": "morning",
}

payload_put = {
    "workday": "monday",
    "shift": "afternoon",
    "notes": "Updated",
}

payload_put_notes_only = {
    "workday": "tuesday",
    "notes": "Notes only",
}


# ---------------------------------------------------------------------
# GET /api/part-time/{employee_number} — invalid / not found
# ---------------------------------------------------------------------
def test_part_time_list_rejects_workday_query_param(client, sample_employee):
    """GET list must not accept ``?workday=`` (use DELETE-one for that)."""
    response = client.get("/api/part-time/M00252?workday=tuesday")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_part_time_list_invalid_employee_number(client, sample_employee):
    response = client.get("/api/part-time/Wrong")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_part_time_list_employee_not_found(client, sample_employee):
    response = client.get("/api/part-time/TEST00753")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


# ---------------------------------------------------------------------
# GET /api/part-time/{employee_number} — list stored rows
# ---------------------------------------------------------------------
def test_part_time_list_returns_stored_slugs_not_today(
    client,
    sample_employee,
    sample_employee_part_time,
):
    """List exposes stored workday slugs; not contextual ``today`` from employee API."""
    response = client.get("/api/part-time/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "A00265"
    assert data["count"] == 2
    assert [row["workday"] for row in data["part_times"]] == ["monday", "tuesday"]
    for row in data["part_times"]:
        assert row["workday"] != "today"
        assert "id" in row
        assert "shift" in row
        assert "notes" in row
        assert "created_at" in row
        assert "updated_at" in row


def test_part_time_list_ordered_by_part_time_stored_workdays(
    client,
    sample_employee,
    part_time_monika_unsorted_rows,
):
    """Rows are sorted by ``PART_TIME_STORED_WORKDAYS``, not insertion order."""
    response = client.get("/api/part-time/M00252")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    workdays = [row["workday"] for row in data["part_times"]]
    assert workdays == sorted(workdays, key=PART_TIME_STORED_WORKDAYS.index)
    assert workdays == [
        "monday",
        "friday",
        WEEKDAYS_WORKDAY,
        ALL_WEEK_WORKDAY,
    ]


def test_part_time_list_empty_for_full_time_employee(client, sample_employee):
    """Full-time employees have no stored rows."""
    response = client.get("/api/part-time/P00370")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "P00370"
    assert data["part_times"] == []
    assert data["count"] == 0


def test_part_time_list_is_public(client, sample_employee, sample_employee_part_time):
    """GET does not require admin authentication."""
    response = client.get("/api/part-time/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2


# ---------------------------------------------------------------------
# POST /api/part-time/{employee_number} — invalid payload
# ---------------------------------------------------------------------
def test_part_time_create_invalid_payload_error_1(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_part_time_create_invalid_payload_error_2(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json={"shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_part_time_create_invalid_payload_error_3(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "today", "shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_part_time_create_invalid_payload_error_4(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "evening"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_SHIFT"


def test_part_time_create_invalid_payload_error_5(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/part-time/M00252",
        headers=headers,
        json={"workday": WEEKDAYS_WORKDAY, "shift": "all-day"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_COMBINATION"

    response = client.post(
        "/api/part-time/M00252",
        headers=headers,
        json={"workday": ALL_WEEK_WORKDAY, "shift": "all-day"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_COMBINATION"


# POST, PUT, and DELETE-all require admin (401 without token; 403 for employee/staff).
@pytest.mark.parametrize(
    ("method", "path", "json_body", "needs_part_time", "check_staff"),
    [
        (
            "post",
            "/api/part-time/M00252",
            {"workday": "monday", "shift": "morning"},
            False,
            True,
        ),
        (
            "put",
            "/api/part-time/A00265",
            {"workday": "monday", "shift": "morning"},
            True,
            False,
        ),
        ("delete", "/api/part-time/A00265", None, True, False),
    ],
)
def test_part_time_mutation_requires_admin(
    client,
    request,
    method,
    path,
    json_body,
    needs_part_time,
    check_staff,
    sample_authentication,
    sample_employee,
):
    """Mutating endpoints reject missing auth and non-admin tokens."""
    if needs_part_time:
        request.getfixturevalue("sample_employee_part_time")

    client_method = getattr(client, method)
    kwargs = {"json": json_body} if json_body is not None else {}

    response = client_method(path, **kwargs)
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "AUTHORIZATION_REQUIRED"

    employee_token = _login_as_employee(client, sample_authentication, sample_employee)
    response = client_method(
        path,
        headers={"Authorization": f"Bearer {employee_token}"},
        **kwargs,
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"

    if check_staff:
        staff_token = _login_as_staff(client, sample_authentication, sample_employee)
        response = client_method(
            path,
            headers={"Authorization": f"Bearer {staff_token}"},
            **kwargs,
        )
        if response.status_code != 403:
            print(response.text)
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"


def test_part_time_create_invalid_employee_number(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/Wrong",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_part_time_create_employee_not_found(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/TEST00753",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_part_time_create_duplicate_workday(
    client,
    sample_authentication,
    sample_employee,
    sample_employee_part_time,
):
    """Duplicate ``(employee, workday)`` is rejected by the DB unique constraint."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"


# ---------------------------------------------------------------------
# POST /api/part-time/{employee_number} — create row
# ---------------------------------------------------------------------
def test_part_time_create(client, sample_authentication, sample_employee):
    """Admin POST creates a stored row with canonical slugs and timestamps."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["workday"] == payload_create["workday"]
    assert data["shift"] == payload_create["shift"]
    assert data["notes"] == payload_create["notes"]
    assert isinstance(data["id"], int)
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    response = client.get("/api/part-time/M00252")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1


def test_part_time_create_defaults_shift_to_all_day(
    client, sample_authentication, sample_employee
):
    """Omitted ``shift`` defaults to ``all-day`` for calendar workdays."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create_default_shift,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["shift"] == "all-day"


# ---------------------------------------------------------------------
# PUT /api/part-time/{employee_number} — invalid payload
# ---------------------------------------------------------------------
def test_part_time_update_invalid_payload_error_1(
    client,
    sample_authentication,
    sample_employee,
    sample_employee_part_time,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
        json={"shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_part_time_update_invalid_payload_error_2(
    client,
    sample_authentication,
    sample_employee,
    sample_employee_part_time,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "today", "shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_part_time_update_invalid_payload_error_3(
    client,
    sample_authentication,
    sample_employee,
    sample_employee_part_time,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "evening"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_SHIFT"


def test_part_time_update_invalid_payload_error_4(
    client, sample_authentication, sample_employee
):
    """Aggregate workdays reject ``all-day`` shift on PUT."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/part-time/M00252",
        headers=headers,
        json=payload_create_aggregate,
    )
    response = client.put(
        "/api/part-time/M00252",
        headers=headers,
        json={"workday": WEEKDAYS_WORKDAY, "shift": "all-day"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_COMBINATION"


def test_part_time_update_not_found(client, sample_authentication, sample_employee):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "friday", "shift": "morning"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "PART_TIME_NOT_FOUND"


def test_part_time_update_invalid_employee_number(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/Wrong",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_part_time_update_employee_not_found(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/TEST00753",
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


# ---------------------------------------------------------------------
# PUT /api/part-time/{employee_number} — update row
# ---------------------------------------------------------------------
def test_part_time_update(
    client, sample_authentication, sample_employee, sample_employee_part_time
):
    """Admin PUT updates shift and notes; workday is lookup key only."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == payload_put["workday"]
    assert data["shift"] == payload_put["shift"]
    assert data["notes"] == payload_put["notes"]

    response = client.get("/api/part-time/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    list_data = response.get_json()
    monday = next(row for row in list_data["part_times"] if row["workday"] == "monday")
    assert monday["shift"] == payload_put["shift"]
    assert monday["notes"] == payload_put["notes"]


def test_part_time_update_notes_only(
    client, sample_authentication, sample_employee, sample_employee_part_time
):
    """Partial PUT may update notes without changing shift."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put_notes_only,
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == payload_put_notes_only["workday"]
    assert data["shift"] == "afternoon"
    assert data["notes"] == payload_put_notes_only["notes"]


# ---------------------------------------------------------------------
# DELETE /api/part-time/{employee_number} — delete all rows
# ---------------------------------------------------------------------
def test_part_time_delete_all_invalid_employee_number(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/Wrong",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_part_time_delete_all_employee_not_found(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/TEST00753",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_part_time_delete_all(
    client, sample_authentication, sample_employee, sample_employee_part_time
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "part-time rows deleted"
    assert data["count"] == 2

    response = client.get("/api/part-time/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0


def test_part_time_delete_all_idempotent(
    client, sample_authentication, sample_employee
):
    """DELETE all is idempotent when no rows exist."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "part-time rows deleted"
    assert data["count"] == 0


def test_part_time_delete_all_restores_full_time_projection(
    client,
    camp_is_monday,
    sample_authentication,
    sample_employee,
    sample_employee_part_time,
):
    """After DELETE all, employee GET shows full-time projection."""
    response = client.get("/api/employees/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["full_time"] is False

    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/A00265",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2

    response = client.get("/api/employees/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["full_time"] is True
    assert data["workday"] == "today"
    assert data["shift"] == "all-day"


# ---------------------------------------------------------------------
# DELETE /api/part-time/{employee_number}?workday= — delete one row
# ---------------------------------------------------------------------
def test_part_time_delete_one_requires_admin(
    client,
    sample_employee_part_time,
):
    """DELETE-one requires admin; tested separately from DELETE-all parametrization."""
    response = client.delete("/api/part-time/A00265?workday=monday")
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "AUTHORIZATION_REQUIRED"


def test_part_time_delete_one_invalid_workday(
    client,
    sample_authentication,
    sample_employee,
    sample_employee_part_time,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/A00265?workday=today",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_part_time_delete_one_not_found(client, sample_authentication, sample_employee):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/M00252?workday=friday",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "PART_TIME_NOT_FOUND"


def test_part_time_delete_one_invalid_employee_number(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/Wrong?workday=monday",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_part_time_delete_one_employee_not_found(
    client, sample_authentication, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/TEST00753?workday=monday",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_part_time_delete_one(
    client, sample_authentication, sample_employee, sample_employee_part_time
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        "/api/part-time/A00265?workday=tuesday",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "part-time row deleted"

    response = client.get("/api/part-time/A00265")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    list_data = response.get_json()
    workdays = [row["workday"] for row in list_data["part_times"]]
    assert workdays == ["monday"]


def test_part_time_delete_one_aggregate_workday(
    client, sample_authentication, sample_employee
):
    """DELETE-one accepts stored aggregate slugs such as ``weekdays``."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/part-time/M00252",
        headers=headers,
        json=payload_create_aggregate,
    )
    response = client.delete(
        f"/api/part-time/M00252?workday={WEEKDAYS_WORKDAY}",
        headers=headers,
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "part-time row deleted"

    response = client.get("/api/part-time/M00252")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0
