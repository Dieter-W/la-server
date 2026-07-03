"""Company jobs max CRUD API tests (``/api/company-jobs-max``)."""

from urllib.parse import quote

import pytest

from app.camp_time import CAMP_SHIFTS
from app.models import CompanyJobsMax
from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    PART_TIME_STORED_WORKDAYS,
    WEEKDAYS_WORKDAY,
)
from tests.test_part_time_helpers import seed_company_jobs_max_rows
from tests.test_utils import _login_as_admin, _login_as_employee, _login_as_staff

payload_create = {
    "workday": "wednesday",
    "shift": "morning",
    "jobs_max": 5,
    "notes": "Camp day cap",
}

payload_create_default_shift = {
    "workday": "friday",
    "jobs_max": 3,
}

payload_create_aggregate = {
    "workday": WEEKDAYS_WORKDAY,
    "shift": "morning",
    "jobs_max": 4,
}

payload_put = {
    "workday": "monday",
    "shift": "afternoon",
    "jobs_max": 7,
    "notes": "Updated",
}

payload_put_notes_only = {
    "workday": "tuesday",
    "shift": "morning",
    "notes": "Notes only",
}


def _company_jobs_max_path(company_name: str) -> str:
    return f"/api/company-jobs-max/{quote(company_name, safe='')}"


@pytest.fixture
def sample_company_jobs_max(app, sample_company):
    """Bank (id 1): Monday morning + Tuesday afternoon schedule rows."""
    with app.app_context():
        session = app.SessionLocal()
        seed_company_jobs_max_rows(
            session,
            [
                (1, "monday", "morning", 5),
                (1, "tuesday", "afternoon", 2),
            ],
        )
        row = session.query(CompanyJobsMax).order_by(CompanyJobsMax.id.desc()).first()
        yield row
        session.close()


@pytest.fixture
def company_jobs_max_bank_unsorted_rows(app, sample_company):
    """Bank (id 1): rows in non-canonical order for list-sort tests."""
    with app.app_context():
        session = app.SessionLocal()
        seed_company_jobs_max_rows(
            session,
            [
                (1, "friday", "morning", 1),
                (1, "monday", "afternoon", 2),
                (1, WEEKDAYS_WORKDAY, "morning", 3),
                (1, ALL_WEEK_WORKDAY, "afternoon", 4),
            ],
        )
        session.close()


# ---------------------------------------------------------------------
# GET /api/company-jobs-max/{company_name} — invalid / not found
# ---------------------------------------------------------------------
def test_company_jobs_max_list_rejects_workday_query_param(client, sample_company):
    """GET list must not accept ``?workday=``."""
    response = client.get(f"{_company_jobs_max_path('Bank')}?workday=tuesday")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_company_jobs_max_list_rejects_shift_query_param(client, sample_company):
    """GET list must not accept ``?shift=``."""
    response = client.get(f"{_company_jobs_max_path('Bank')}?shift=morning")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_SHIFT"


def test_company_jobs_max_list_company_not_found(client, sample_company):
    response = client.get(_company_jobs_max_path("Wrong"))
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


# ---------------------------------------------------------------------
# GET /api/company-jobs-max/{company_name} — list stored rows
# ---------------------------------------------------------------------
def test_company_jobs_max_list_returns_stored_slugs(
    client,
    sample_company,
    sample_company_jobs_max,
):
    """List exposes stored workday/shift slugs; not contextual labels from company API."""
    response = client.get(_company_jobs_max_path("Bank"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["company_name"] == "Bank"
    assert data["count"] == 2
    assert [row["workday"] for row in data["company_jobs_max"]] == [
        "monday",
        "tuesday",
    ]
    for row in data["company_jobs_max"]:
        assert row["workday"] != "today"
        assert "id" in row
        assert "shift" in row
        assert "jobs_max" in row
        assert "notes" in row
        assert "created_at" in row
        assert "updated_at" in row


def test_company_jobs_max_list_ordered_by_stored_workdays_and_shifts(
    client,
    sample_company,
    company_jobs_max_bank_unsorted_rows,
):
    """Rows are sorted by stored workday order then shift order."""
    response = client.get(_company_jobs_max_path("Bank"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    rows = data["company_jobs_max"]
    workday_shift = [(row["workday"], row["shift"]) for row in rows]
    assert workday_shift == sorted(
        workday_shift,
        key=lambda pair: (
            PART_TIME_STORED_WORKDAYS.index(pair[0]),
            CAMP_SHIFTS.index(pair[1]),
        ),
    )
    assert workday_shift == [
        ("monday", "afternoon"),
        ("friday", "morning"),
        (WEEKDAYS_WORKDAY, "morning"),
        (ALL_WEEK_WORKDAY, "afternoon"),
    ]


def test_company_jobs_max_list_empty_for_default_cap_company(client, sample_company):
    """Companies with no schedule rows return an empty list."""
    response = client.get(_company_jobs_max_path("Arbeitsamt"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["company_name"] == "Arbeitsamt"
    assert data["company_jobs_max"] == []
    assert data["count"] == 0


def test_company_jobs_max_list_is_public(
    client,
    sample_company,
    sample_company_jobs_max,
):
    """GET does not require admin authentication."""
    response = client.get(_company_jobs_max_path("Bank"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2


# ---------------------------------------------------------------------
# POST /api/company-jobs-max/{company_name} — invalid payload
# ---------------------------------------------------------------------
def test_company_jobs_max_create_invalid_payload_error_1(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_company_jobs_max_create_invalid_payload_error_2(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json={"shift": "morning", "jobs_max": 5},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_company_jobs_max_create_invalid_payload_error_3(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "wednesday", "shift": "morning"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_company_jobs_max_create_invalid_payload_error_4(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "today", "shift": "morning", "jobs_max": 5},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_company_jobs_max_create_invalid_payload_error_5(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "evening", "jobs_max": 5},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_SHIFT"


def test_company_jobs_max_create_invalid_payload_error_6(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers=headers,
        json={"workday": WEEKDAYS_WORKDAY, "shift": "all-day", "jobs_max": 5},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_COMBINATION"

    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers=headers,
        json={"workday": ALL_WEEK_WORKDAY, "shift": "all-day", "jobs_max": 5},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_COMBINATION"


def test_company_jobs_max_create_invalid_jobs_max(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    headers = {"Authorization": f"Bearer {token}"}
    for invalid_value in ("five", -1, True):
        response = client.post(
            _company_jobs_max_path("Arbeitsamt"),
            headers=headers,
            json={"workday": "monday", "shift": "morning", "jobs_max": invalid_value},
        )
        if response.status_code != 400:
            print(response.text)
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "INVALID_JOBS_MAX"


@pytest.mark.parametrize(
    ("method", "path", "json_body", "needs_rows", "check_staff"),
    [
        (
            "post",
            "/api/company-jobs-max/Arbeitsamt",
            {"workday": "monday", "shift": "morning", "jobs_max": 5},
            False,
            True,
        ),
        (
            "put",
            "/api/company-jobs-max/Bank",
            {"workday": "monday", "shift": "morning", "jobs_max": 6},
            True,
            False,
        ),
        ("delete", "/api/company-jobs-max/Bank", None, True, False),
    ],
)
def test_company_jobs_max_mutation_requires_admin(
    client,
    request,
    method,
    path,
    json_body,
    needs_rows,
    check_staff,
    sample_authentication,
    sample_company,
    sample_employee,
):
    """Mutating endpoints reject missing auth and non-admin tokens."""
    if needs_rows:
        request.getfixturevalue("sample_company_jobs_max")

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


def test_company_jobs_max_create_company_not_found(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Wrong"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning", "jobs_max": 5},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_company_jobs_max_create_duplicate_workday_shift(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    """Duplicate ``(company, workday, shift)`` is rejected by the DB unique constraint."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning", "jobs_max": 9},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"


def test_company_jobs_max_create_allows_same_workday_different_shift(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    """Morning and afternoon caps may coexist on the same calendar workday."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "afternoon", "jobs_max": 3},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["workday"] == "monday"
    assert data["shift"] == "afternoon"
    assert data["jobs_max"] == 3


# ---------------------------------------------------------------------
# POST /api/company-jobs-max/{company_name} — create row
# ---------------------------------------------------------------------
def test_company_jobs_max_create(
    client, sample_authentication, sample_company, sample_employee
):
    """Admin POST creates a stored row with canonical slugs and timestamps."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["workday"] == payload_create["workday"]
    assert data["shift"] == payload_create["shift"]
    assert data["jobs_max"] == payload_create["jobs_max"]
    assert data["notes"] == payload_create["notes"]
    assert isinstance(data["id"], int)
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    response = client.get(_company_jobs_max_path("Arbeitsamt"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1


def test_company_jobs_max_create_defaults_shift_to_all_day(
    client, sample_authentication, sample_company, sample_employee
):
    """Omitted ``shift`` defaults to ``all-day`` for calendar workdays."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create_default_shift,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["shift"] == "all-day"


# ---------------------------------------------------------------------
# PUT /api/company-jobs-max/{company_name} — invalid payload
# ---------------------------------------------------------------------
def test_company_jobs_max_update_invalid_payload_error_1(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"jobs_max": 6},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_company_jobs_max_update_invalid_payload_error_2(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "today", "shift": "morning", "jobs_max": 6},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_company_jobs_max_update_invalid_payload_error_3(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "evening", "jobs_max": 6},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_SHIFT"


def test_company_jobs_max_update_invalid_jobs_max(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning", "jobs_max": -2},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_JOBS_MAX"


def test_company_jobs_max_update_not_found(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "friday", "shift": "morning", "jobs_max": 6},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_JOBS_MAX_NOT_FOUND"


def test_company_jobs_max_update_company_not_found(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.put(
        _company_jobs_max_path("Wrong"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "morning", "jobs_max": 6},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


# ---------------------------------------------------------------------
# PUT /api/company-jobs-max/{company_name} — update row
# ---------------------------------------------------------------------
def test_company_jobs_max_update(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    """Admin PUT updates jobs_max and notes; workday/shift are lookup keys only."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    client.post(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "monday", "shift": "afternoon", "jobs_max": 1},
    )
    response = client.put(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == payload_put["workday"]
    assert data["shift"] == payload_put["shift"]
    assert data["jobs_max"] == payload_put["jobs_max"]
    assert data["notes"] == payload_put["notes"]

    response = client.get(_company_jobs_max_path("Bank"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    list_data = response.get_json()
    monday_afternoon = next(
        row
        for row in list_data["company_jobs_max"]
        if row["workday"] == "monday" and row["shift"] == "afternoon"
    )
    assert monday_afternoon["jobs_max"] == payload_put["jobs_max"]
    assert monday_afternoon["notes"] == payload_put["notes"]


def test_company_jobs_max_update_notes_only(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    """Partial PUT may update notes without changing jobs_max."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    client.post(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json={"workday": "tuesday", "shift": "morning", "jobs_max": 8},
    )
    response = client.put(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put_notes_only,
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == payload_put_notes_only["workday"]
    assert data["shift"] == payload_put_notes_only["shift"]
    assert data["jobs_max"] == 8
    assert data["notes"] == payload_put_notes_only["notes"]


# ---------------------------------------------------------------------
# DELETE /api/company-jobs-max/{company_name} — delete all rows
# ---------------------------------------------------------------------
def test_company_jobs_max_delete_all_company_not_found(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        _company_jobs_max_path("Wrong"),
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_company_jobs_max_delete_all(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        _company_jobs_max_path("Bank"),
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "company jobs max rows deleted"
    assert data["count"] == 2

    response = client.get(_company_jobs_max_path("Bank"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0


def test_company_jobs_max_delete_all_idempotent(
    client, sample_authentication, sample_company, sample_employee
):
    """DELETE all is idempotent when no rows exist."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        _company_jobs_max_path("Arbeitsamt"),
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "company jobs max rows deleted"
    assert data["count"] == 0


# ---------------------------------------------------------------------
# DELETE /api/company-jobs-max/{company_name}?workday=&shift= — delete one
# ---------------------------------------------------------------------
def test_company_jobs_max_delete_one_requires_admin(
    client,
    sample_company,
    sample_company_jobs_max,
):
    """DELETE-one requires admin; tested separately from DELETE-all parametrization."""
    response = client.delete(
        f"{_company_jobs_max_path('Bank')}?workday=tuesday&shift=afternoon"
    )
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "AUTHORIZATION_REQUIRED"


def test_company_jobs_max_delete_one_requires_both_query_params(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        f"{_company_jobs_max_path('Bank')}?workday=tuesday",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_SHIFT"


def test_company_jobs_max_delete_one_invalid_workday(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        f"{_company_jobs_max_path('Bank')}?workday=today&shift=morning",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_PART_TIME_WORKDAY"


def test_company_jobs_max_delete_one_not_found(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        f"{_company_jobs_max_path('Arbeitsamt')}?workday=friday&shift=morning",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_JOBS_MAX_NOT_FOUND"


def test_company_jobs_max_delete_one_company_not_found(
    client, sample_authentication, sample_company, sample_employee
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        f"{_company_jobs_max_path('Wrong')}?workday=monday&shift=morning",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_company_jobs_max_delete_one(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_company_jobs_max,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)
    response = client.delete(
        f"{_company_jobs_max_path('Bank')}?workday=tuesday&shift=afternoon",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "company jobs max row deleted"

    response = client.get(_company_jobs_max_path("Bank"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    list_data = response.get_json()
    remaining = [
        (row["workday"], row["shift"]) for row in list_data["company_jobs_max"]
    ]
    assert remaining == [("monday", "morning")]


def test_company_jobs_max_delete_one_aggregate_workday(
    client, sample_authentication, sample_company, sample_employee
):
    """DELETE-one accepts stored aggregate slugs such as ``weekdays``."""
    token = _login_as_admin(client, sample_authentication, sample_employee)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        _company_jobs_max_path("Arbeitsamt"),
        headers=headers,
        json=payload_create_aggregate,
    )
    response = client.delete(
        f"{_company_jobs_max_path('Arbeitsamt')}?workday={WEEKDAYS_WORKDAY}&shift=morning",
        headers=headers,
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "company jobs max row deleted"

    response = client.get(_company_jobs_max_path("Arbeitsamt"))
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0
