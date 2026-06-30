"""Attendance API tests (check-in / check-out, lists, per-person history)."""

from datetime import date

from app.schemas.part_time import ALL_WEEK_WORKDAY, WEEKDAYS_WORKDAY
from tests.test_camp_time import CAMP_MONDAY, CAMP_WEDNESDAY, camp_today_patch
from tests.test_utils import (
    _login_as_admin,
    _login_as_employee,
    _login_as_staff,
)

CAMP_MONDAY_DATE = CAMP_MONDAY.date()
CAMP_WEDNESDAY_DATE = CAMP_WEDNESDAY.date()


# ---------------------------------------------------------------------
# POST check-in / check-out — request body rejected
# ---------------------------------------------------------------------
def test_attendance_check_in_post_rejects_request_body(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """POST check-in rejects any request body (including ``{}``)."""
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_NOT_ALLOWED"

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201


def test_attendance_check_out_post_rejects_request_body(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """POST check-out rejects any request body (including ``{}``)."""
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_NOT_ALLOWED"

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200


# ---------------------------------------------------------------------
# POST check-in / check-out — auth (staff or admin required)
# ---------------------------------------------------------------------
def test_attendance_check_in_post_requires_auth(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """POST check-in without token returns 401."""
    response = client.post("/api/attendance/check-in/M00252")
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "AUTHORIZATION_REQUIRED"


def test_attendance_check_in_post_forbidden_employee(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """POST check-in with employee token returns 403."""
    token = _login_as_employee(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"


def test_attendance_check_out_post_requires_auth(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """POST check-out without token returns 401."""
    response = client.post("/api/attendance/check-out/M00252")
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "AUTHORIZATION_REQUIRED"


def test_attendance_check_out_post_forbidden_employee(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """POST check-out with employee token returns 403."""
    token = _login_as_employee(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"


# ---------------------------------------------------------------------
# POST /api/attendance/check-in/{employee_number} — errors
# ---------------------------------------------------------------------
def test_attendance_check_in_invalid_employee_number(
    client,
    sample_authentication,
    sample_employee,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/Wrong",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_attendance_check_in_employee_not_found(
    client,
    sample_authentication,
    sample_employee,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/TEST00753",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_attendance_check_in_inactive_employee(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00155",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"


def test_attendance_check_in_duplicate(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"


# ---------------------------------------------------------------------
# POST /api/attendance/check-in/{employee_number} — success
# ---------------------------------------------------------------------
def test_attendance_check_in_staff_success(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["employee_number"] == "M00252"
    assert data["camp_date"] == CAMP_MONDAY_DATE.isoformat()
    assert data["checkin_at"] is not None
    assert data["checkout_at"] is None


def test_attendance_check_in_admin_success(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_admin(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/A00265",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["employee_number"] == "A00265"
    assert data["camp_date"] == CAMP_MONDAY_DATE.isoformat()


# ---------------------------------------------------------------------
# POST /api/attendance/check-out/{employee_number} — errors
# ---------------------------------------------------------------------
def test_attendance_check_out_without_check_in(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "ATTENDANCE_NOT_CHECKED_IN"


def test_attendance_check_out_duplicate(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"


# ---------------------------------------------------------------------
# POST /api/attendance/check-out/{employee_number} — success
# ---------------------------------------------------------------------
def test_attendance_check_out_staff_success(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "M00252"
    assert data["checkout_at"] is not None


# ---------------------------------------------------------------------
# GET /api/attendance/check-ins and GET /api/attendance/check-outs — errors
# ---------------------------------------------------------------------
def test_attendance_check_ins_invalid_workday_weekdays(client, sample_employee):
    response = client.get("/api/attendance/check-ins?workday=weekdays")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_ATTENDANCE_WORKDAY"


def test_attendance_check_ins_invalid_workday_all_week(client, sample_employee):
    response = client.get("/api/attendance/check-ins?workday=all-week")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_ATTENDANCE_WORKDAY"


def test_attendance_check_ins_invalid_workday_all(client, sample_employee):
    response = client.get("/api/attendance/check-ins?workday=all")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_ATTENDANCE_WORKDAY"


def test_attendance_check_outs_invalid_workday_weekdays(client, sample_employee):
    response = client.get("/api/attendance/check-outs?workday=weekdays")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_ATTENDANCE_WORKDAY"


# ---------------------------------------------------------------------
# GET /api/attendance/check-ins and GET /api/attendance/check-outs — success
# ---------------------------------------------------------------------
def test_attendance_check_ins_default_today_empty(
    client,
    sample_employee,
    camp_today_is_monday,
):
    response = client.get("/api/attendance/check-ins")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == "today"
    assert data["camp_date"] == CAMP_MONDAY_DATE.isoformat()
    assert data["check_ins"] == []
    assert data["count"] == 0


def test_attendance_check_ins_sorted_by_employee_number(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/P00370",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-in/A00265",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/attendance/check-ins")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    numbers = [row["employee_number"] for row in data["check_ins"]]
    assert numbers == ["A00265", "M00252", "P00370"]
    assert data["count"] == 3
    for row in data["check_ins"]:
        assert "first_name" in row
        assert "last_name" in row
        assert row["checkin_at"] is not None
        assert row["checkout_at"] is None


def test_attendance_check_ins_workday_monday(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/attendance/check-ins?workday=monday")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == "monday"
    assert data["camp_date"] == CAMP_MONDAY_DATE.isoformat()
    assert data["count"] == 1


def test_attendance_check_ins_workday_wednesday_same_camp_week(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    """``?workday=wednesday`` on camp Monday resolves to Wednesday of the same week."""
    response = client.get("/api/attendance/check-ins?workday=wednesday")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == "wednesday"
    assert data["camp_date"] == CAMP_WEDNESDAY_DATE.isoformat()
    assert data["count"] == 0

    token = _login_as_staff(client, sample_authentication, sample_employee)
    with camp_today_patch(CAMP_WEDNESDAY):
        response = client.post(
            "/api/attendance/check-in/M00252",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201

    response = client.get("/api/attendance/check-ins?workday=wednesday")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["check_ins"][0]["employee_number"] == "M00252"


def test_attendance_check_outs_only_checked_out_subset(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-in/A00265",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/attendance/check-outs")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["check_outs"] == []
    assert data["count"] == 0

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.get("/api/attendance/check-outs")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["check_outs"][0]["employee_number"] == "M00252"
    assert data["check_outs"][0]["checkout_at"] is not None


def test_attendance_lists_are_public(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/attendance/check-ins")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1

    response = client.get("/api/attendance/check-outs")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0


# ---------------------------------------------------------------------
# GET /api/attendance/{employee_number} — errors
# ---------------------------------------------------------------------
def test_attendance_history_invalid_employee_number(client, sample_employee):
    response = client.get("/api/attendance/Wrong")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_attendance_history_employee_not_found(client, sample_employee):
    response = client.get("/api/attendance/TEST00753")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_attendance_history_invalid_workday(client, sample_employee):
    response = client.get(f"/api/attendance/M00252?workday={ALL_WEEK_WORKDAY}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_ATTENDANCE_WORKDAY"

    response = client.get(f"/api/attendance/M00252?workday={WEEKDAYS_WORKDAY}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_ATTENDANCE_WORKDAY"


# ---------------------------------------------------------------------
# GET /api/attendance/{employee_number} — success
# ---------------------------------------------------------------------
def test_attendance_history_full_history_descending(
    client,
    sample_authentication,
    sample_employee,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    with camp_today_patch(CAMP_MONDAY):
        response = client.post(
            "/api/attendance/check-in/M00252",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201

        response = client.post(
            "/api/attendance/check-out/M00252",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200

    with camp_today_patch(CAMP_WEDNESDAY):
        response = client.post(
            "/api/attendance/check-in/M00252",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201

    response = client.get("/api/attendance/M00252")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "M00252"
    assert data["count"] == 2
    assert "workday" not in data
    assert "camp_date" not in data

    dates = [row["camp_date"] for row in data["attendances"]]
    assert dates == [
        CAMP_WEDNESDAY_DATE.isoformat(),
        CAMP_MONDAY_DATE.isoformat(),
    ]
    assert data["attendances"][0]["checkout_at"] is None
    assert data["attendances"][1]["checkout_at"] is not None


def test_attendance_history_filtered_by_workday(
    client,
    sample_authentication,
    sample_employee,
    camp_today_is_monday,
):
    token = _login_as_staff(client, sample_authentication, sample_employee)

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/attendance/M00252?workday=today")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == "today"
    assert data["camp_date"] == CAMP_MONDAY_DATE.isoformat()
    assert data["count"] == 1
    assert data["attendances"][0]["camp_date"] == CAMP_MONDAY_DATE.isoformat()


def test_attendance_history_filtered_day_no_row(
    client,
    sample_employee,
    camp_today_is_monday,
):
    response = client.get("/api/attendance/M00252?workday=friday")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["workday"] == "friday"
    assert data["camp_date"] == date(2026, 5, 22).isoformat()
    assert data["attendances"] == []
    assert data["count"] == 0
