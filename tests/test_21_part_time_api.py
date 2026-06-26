"""Part-time CRUD API tests (``/api/part-time``)."""

import pytest

from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    PART_TIME_STORED_WORKDAYS,
    WEEKDAYS_WORKDAY,
)
from tests.test_utils import assert_status

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
    assert (
        assert_status(client.get("/api/part-time/M00252?workday=tuesday"), 400)["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )


def test_part_time_list_invalid_employee_number(client, sample_employee):
    assert (
        assert_status(client.get("/api/part-time/Wrong"), 400)["error"]
        == "EMPLOYEE_NUMBER_WRONG"
    )


def test_part_time_list_employee_not_found(client, sample_employee):
    assert (
        assert_status(client.get("/api/part-time/TEST00753"), 404)["error"]
        == "EMPLOYEE_NOT_FOUND"
    )


# ---------------------------------------------------------------------
# GET /api/part-time/{employee_number} — list stored rows
# ---------------------------------------------------------------------
def test_part_time_list_returns_stored_slugs_not_today(
    client,
    sample_employee,
    sample_employee_part_time,
):
    """List exposes stored workday slugs; not contextual ``today`` from employee API."""
    data = assert_status(client.get("/api/part-time/A00265"), 200)
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
    data = assert_status(client.get("/api/part-time/M00252"), 200)
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
    data = assert_status(client.get("/api/part-time/P00370"), 200)
    assert data["employee_number"] == "P00370"
    assert data["part_times"] == []
    assert data["count"] == 0


def test_part_time_list_is_public(client, sample_employee, sample_employee_part_time):
    """GET does not require admin authentication."""
    assert assert_status(client.get("/api/part-time/A00265"), 200)["count"] == 2


# ---------------------------------------------------------------------
# POST /api/part-time/{employee_number} — invalid payload
# ---------------------------------------------------------------------
def test_part_time_create_invalid_payload_error_1(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json="{wrong = JSON}",
            ),
            400,
        )["error"]
        == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"
    )


def test_part_time_create_invalid_payload_error_2(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"shift": "morning"},
            ),
            400,
        )["error"]
        == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"
    )


def test_part_time_create_invalid_payload_error_3(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"workday": "today", "shift": "morning"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )


def test_part_time_create_invalid_payload_error_4(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"workday": "monday", "shift": "evening"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_SHIFT"
    )


def test_part_time_create_invalid_payload_error_5(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"workday": WEEKDAYS_WORKDAY, "shift": "all-day"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_COMBINATION"
    )

    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"workday": ALL_WEEK_WORKDAY, "shift": "all-day"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_COMBINATION"
    )


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
    employee_headers,
    staff_headers,
):
    """Mutating endpoints reject missing auth and non-admin tokens."""
    if needs_part_time:
        request.getfixturevalue("sample_employee_part_time")

    client_method = getattr(client, method)
    kwargs = {"json": json_body} if json_body is not None else {}

    assert (
        assert_status(client_method(path, **kwargs), 401)["error"]
        == "AUTHORIZATION_REQUIRED"
    )

    assert (
        assert_status(client_method(path, headers=employee_headers, **kwargs), 403)[
            "error"
        ]
        == "FORBIDDEN_WRONG_AUTH_GROUP"
    )

    if check_staff:
        assert (
            assert_status(client_method(path, headers=staff_headers, **kwargs), 403)[
                "error"
            ]
            == "FORBIDDEN_WRONG_AUTH_GROUP"
        )


def test_part_time_create_invalid_employee_number(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/Wrong",
                headers=admin_headers,
                json={"workday": "monday", "shift": "morning"},
            ),
            400,
        )["error"]
        == "EMPLOYEE_NUMBER_WRONG"
    )


def test_part_time_create_employee_not_found(client, admin_headers):
    assert (
        assert_status(
            client.post(
                "/api/part-time/TEST00753",
                headers=admin_headers,
                json={"workday": "monday", "shift": "morning"},
            ),
            404,
        )["error"]
        == "EMPLOYEE_NOT_FOUND"
    )


def test_part_time_create_duplicate_workday(
    client,
    admin_headers,
    sample_employee_part_time,
):
    """Duplicate ``(employee, workday)`` is rejected by the DB unique constraint."""
    assert (
        assert_status(
            client.post(
                "/api/part-time/A00265",
                headers=admin_headers,
                json={"workday": "monday", "shift": "morning"},
            ),
            409,
        )["error"]
        == "CONSTRAINT_VIOLATION"
    )


# ---------------------------------------------------------------------
# POST /api/part-time/{employee_number} — create row
# ---------------------------------------------------------------------
def test_part_time_create(client, admin_headers):
    """Admin POST creates a stored row with canonical slugs and timestamps."""
    data = assert_status(
        client.post(
            "/api/part-time/M00252",
            headers=admin_headers,
            json=payload_create,
        ),
        201,
    )
    assert data["workday"] == payload_create["workday"]
    assert data["shift"] == payload_create["shift"]
    assert data["notes"] == payload_create["notes"]
    assert isinstance(data["id"], int)
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    assert assert_status(client.get("/api/part-time/M00252"), 200)["count"] == 1


def test_part_time_create_defaults_shift_to_all_day(client, admin_headers):
    """Omitted ``shift`` defaults to ``all-day`` for calendar workdays."""
    assert (
        assert_status(
            client.post(
                "/api/part-time/M00252",
                headers=admin_headers,
                json=payload_create_default_shift,
            ),
            201,
        )["shift"]
        == "all-day"
    )


# ---------------------------------------------------------------------
# PUT /api/part-time/{employee_number} — invalid payload
# ---------------------------------------------------------------------
def test_part_time_update_invalid_payload_error_1(
    client,
    admin_headers,
    sample_employee_part_time,
):
    assert (
        assert_status(
            client.put(
                "/api/part-time/A00265",
                headers=admin_headers,
                json={"shift": "morning"},
            ),
            400,
        )["error"]
        == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"
    )


def test_part_time_update_invalid_payload_error_2(
    client,
    admin_headers,
    sample_employee_part_time,
):
    assert (
        assert_status(
            client.put(
                "/api/part-time/A00265",
                headers=admin_headers,
                json={"workday": "today", "shift": "morning"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )


def test_part_time_update_invalid_payload_error_3(
    client,
    admin_headers,
    sample_employee_part_time,
):
    assert (
        assert_status(
            client.put(
                "/api/part-time/A00265",
                headers=admin_headers,
                json={"workday": "monday", "shift": "evening"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_SHIFT"
    )


def test_part_time_update_invalid_payload_error_4(client, admin_headers):
    """Aggregate workdays reject ``all-day`` shift on PUT."""
    client.post(
        "/api/part-time/M00252",
        headers=admin_headers,
        json=payload_create_aggregate,
    )
    assert (
        assert_status(
            client.put(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"workday": WEEKDAYS_WORKDAY, "shift": "all-day"},
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_COMBINATION"
    )


def test_part_time_update_not_found(client, admin_headers):
    assert (
        assert_status(
            client.put(
                "/api/part-time/M00252",
                headers=admin_headers,
                json={"workday": "friday", "shift": "morning"},
            ),
            404,
        )["error"]
        == "PART_TIME_NOT_FOUND"
    )


def test_part_time_update_invalid_employee_number(client, admin_headers):
    assert (
        assert_status(
            client.put(
                "/api/part-time/Wrong",
                headers=admin_headers,
                json={"workday": "monday", "shift": "morning"},
            ),
            400,
        )["error"]
        == "EMPLOYEE_NUMBER_WRONG"
    )


def test_part_time_update_employee_not_found(client, admin_headers):
    assert (
        assert_status(
            client.put(
                "/api/part-time/TEST00753",
                headers=admin_headers,
                json={"workday": "monday", "shift": "morning"},
            ),
            404,
        )["error"]
        == "EMPLOYEE_NOT_FOUND"
    )


# ---------------------------------------------------------------------
# PUT /api/part-time/{employee_number} — update row
# ---------------------------------------------------------------------
def test_part_time_update(client, admin_headers, sample_employee_part_time):
    """Admin PUT updates shift and notes; workday is lookup key only."""
    data = assert_status(
        client.put(
            "/api/part-time/A00265",
            headers=admin_headers,
            json=payload_put,
        ),
        200,
    )
    assert data["workday"] == payload_put["workday"]
    assert data["shift"] == payload_put["shift"]
    assert data["notes"] == payload_put["notes"]

    monday = next(
        row
        for row in assert_status(client.get("/api/part-time/A00265"), 200)["part_times"]
        if row["workday"] == "monday"
    )
    assert monday["shift"] == payload_put["shift"]
    assert monday["notes"] == payload_put["notes"]


def test_part_time_update_notes_only(client, admin_headers, sample_employee_part_time):
    """Partial PUT may update notes without changing shift."""
    data = assert_status(
        client.put(
            "/api/part-time/A00265",
            headers=admin_headers,
            json=payload_put_notes_only,
        ),
        200,
    )
    assert data["workday"] == payload_put_notes_only["workday"]
    assert data["shift"] == "afternoon"
    assert data["notes"] == payload_put_notes_only["notes"]


# ---------------------------------------------------------------------
# DELETE /api/part-time/{employee_number} — delete all rows
# ---------------------------------------------------------------------
def test_part_time_delete_all_invalid_employee_number(client, admin_headers):
    assert (
        assert_status(
            client.delete("/api/part-time/Wrong", headers=admin_headers),
            400,
        )["error"]
        == "EMPLOYEE_NUMBER_WRONG"
    )


def test_part_time_delete_all_employee_not_found(client, admin_headers):
    assert (
        assert_status(
            client.delete("/api/part-time/TEST00753", headers=admin_headers),
            404,
        )["error"]
        == "EMPLOYEE_NOT_FOUND"
    )


def test_part_time_delete_all(client, admin_headers, sample_employee_part_time):
    data = assert_status(
        client.delete("/api/part-time/A00265", headers=admin_headers),
        200,
    )
    assert data["message"] == "part-time rows deleted"
    assert data["count"] == 2
    assert assert_status(client.get("/api/part-time/A00265"), 200)["count"] == 0


def test_part_time_delete_all_idempotent(client, admin_headers):
    """DELETE all is idempotent when no rows exist."""
    data = assert_status(
        client.delete("/api/part-time/M00252", headers=admin_headers),
        200,
    )
    assert data["message"] == "part-time rows deleted"
    assert data["count"] == 0


def test_part_time_delete_all_restores_full_time_projection(
    client,
    camp_is_monday,
    admin_headers,
    sample_employee_part_time,
):
    """After DELETE all, employee GET shows full-time projection."""
    assert assert_status(client.get("/api/employees/A00265"), 200)["full_time"] is False

    assert (
        assert_status(
            client.delete("/api/part-time/A00265", headers=admin_headers),
            200,
        )["count"]
        == 2
    )

    data = assert_status(client.get("/api/employees/A00265"), 200)
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
    assert (
        assert_status(client.delete("/api/part-time/A00265?workday=monday"), 401)[
            "error"
        ]
        == "AUTHORIZATION_REQUIRED"
    )


def test_part_time_delete_one_invalid_workday(
    client,
    admin_headers,
    sample_employee_part_time,
):
    assert (
        assert_status(
            client.delete(
                "/api/part-time/A00265?workday=today",
                headers=admin_headers,
            ),
            400,
        )["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )


def test_part_time_delete_one_not_found(client, admin_headers):
    assert (
        assert_status(
            client.delete(
                "/api/part-time/M00252?workday=friday",
                headers=admin_headers,
            ),
            404,
        )["error"]
        == "PART_TIME_NOT_FOUND"
    )


def test_part_time_delete_one_invalid_employee_number(client, admin_headers):
    assert (
        assert_status(
            client.delete(
                "/api/part-time/Wrong?workday=monday",
                headers=admin_headers,
            ),
            400,
        )["error"]
        == "EMPLOYEE_NUMBER_WRONG"
    )


def test_part_time_delete_one_employee_not_found(client, admin_headers):
    assert (
        assert_status(
            client.delete(
                "/api/part-time/TEST00753?workday=monday",
                headers=admin_headers,
            ),
            404,
        )["error"]
        == "EMPLOYEE_NOT_FOUND"
    )


def test_part_time_delete_one(client, admin_headers, sample_employee_part_time):
    assert (
        assert_status(
            client.delete(
                "/api/part-time/A00265?workday=tuesday",
                headers=admin_headers,
            ),
            200,
        )["message"]
        == "part-time row deleted"
    )

    workdays = [
        row["workday"]
        for row in assert_status(client.get("/api/part-time/A00265"), 200)["part_times"]
    ]
    assert workdays == ["monday"]


def test_part_time_delete_one_aggregate_workday(client, admin_headers):
    """DELETE-one accepts stored aggregate slugs such as ``weekdays``."""
    client.post(
        "/api/part-time/M00252",
        headers=admin_headers,
        json=payload_create_aggregate,
    )
    assert (
        assert_status(
            client.delete(
                f"/api/part-time/M00252?workday={WEEKDAYS_WORKDAY}",
                headers=admin_headers,
            ),
            200,
        )["message"]
        == "part-time row deleted"
    )
    assert assert_status(client.get("/api/part-time/M00252"), 200)["count"] == 0
