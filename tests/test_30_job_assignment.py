"""Company API tests"""

from unittest.mock import patch

from app.utils import create_job_assignment_number

from tests.test_utils import (
    _login_as_admin,
    _login_as_employee,
    _login_as_staff,
)

# from urllib.parse import quote

payload_create = {
    "company_name": "Arbeitsamt",
    "employee_number": "A00265",
    "notes": "Created by create test",
}


payload_put = {
    "company_name": "Kitchen",
    "jobs_max": 5,
    "hourly_pay": 99,
    "active": False,
    "notes": "Updated by test",
}


# ---------------------------------------------------------------------
# POST /job-assignments — invalid payload
# ---------------------------------------------------------------------
def test_job_assignments_create_invalid_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST with non-JSON body returns 400 REQUEST_BODY_MUST_BE_A_JSON_OBJECT."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_job_assignments_create_invalid_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST without company_name returns 400 REQUIRED_JSON_INPUT_MISSING_OR_EMPTY."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "Test"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_job_assignments_create_invalid_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST without employee_number returns 400 REQUIRED_JSON_INPUT_MISSING_OR_EMPTY."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Test"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_job_assignments_create_invalid_payload_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST with empty company_name returns 400 REQUIRED_JSON_INPUT_MISSING_OR_EMPTY."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "", "employee_number": "Test"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_job_assignments_create_invalid_payload_error_5(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST with empty employee_number returns 400 REQUIRED_JSON_INPUT_MISSING_OR_EMPTY."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Test", "employee_number": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_job_assignments_create_invalid_payload_error_6(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST with invalid employee_number returns 400 EMPLOYEE_NUMBER_WRONG_IN_JSON."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Test", "employee_number": "Wrong"}, # fmt: skip
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


# ---------------------------------------------------------------------
# POST /job-assignments/reset — invalid payload
# ---------------------------------------------------------------------
def test_job_assignments_reset_invalid_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST reset with non-JSON body returns 400 REQUEST_BODY_MUST_BE_A_JSON_OBJECT."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_job_assignments_reset_invalid_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST reset without company_name returns 400 REQUIRED_JSON_INPUT_MISSING_OR_EMPTY."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"test": "test"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_job_assignments_reset_invalid_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    """POST reset with empty company_name returns 400 REQUIRED_JSON_INPUT_MISSING_OR_EMPTY."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


# ---------------------------------------------------------------------
# Get-all job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_get_ok(client, sample_company, sample_employee, sample_job_assignment,):  # fmt: skip
    """GET /api/job-assignments returns 200 with seeded assignments and matching count."""
    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["job_assignments"], list)
    assert len(data["job_assignments"]) == 2
    assert data["count"] == 2
    assert any(
        job_data["id"] == sample_job_assignment.id
        for job_data in data["job_assignments"]
    )
    assert any(
        job_data["company_id"] == sample_job_assignment.company_id
        for job_data in data["job_assignments"]
    )
    assert any(
        job_data["employee_id"] == sample_job_assignment.employee_id
        for job_data in data["job_assignments"]
    )
    assert any(
        job_data["notes"] == sample_job_assignment.notes
        for job_data in data["job_assignments"]
    )

def test_job_assignments_get_ok_empty(client, sample_company, sample_employee,):  # fmt: skip
    """GET /api/job-assignments with no rows returns 200, empty list, and count 0."""
    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["job_assignments"], list)
    assert len(data["job_assignments"]) == 0
    assert data["job_assignments"] == []
    assert data["count"] == 0

# ---------------------------------------------------------------------
# Create job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_create_ok(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """POST creates assignment with generated number and increments list count."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["job_assignment_number"] == create_job_assignment_number(3)
    assert data["id"] == 3
    # assert data["company_id"] == sample_company.id
    # assert data["employee_id"] == sample_employee.id
    # assert data["notes"] == "Created by create test"
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    response = client.get("/api/job-assignments")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 3

def test_job_assignments_create_error_1(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """POST with unknown company returns 404 COMPANY_NOT_FOUND."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Wrong"
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_job_assignments_create_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """POST with inactive company returns 400 COMPANY_NOT_ACTIVE."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Bank"
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_ACTIVE"


def test_job_assignments_create_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """POST with unknown employee returns 404 EMPLOYEE_NOT_FOUND."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "TEST00753"
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404

    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

def test_job_assignments_create_error_4(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """POST with inactive employee returns 400 EMPLOYEE_NOT_ACTIVE."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "M00155"
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"


def test_job_assignments_create_error_5(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """Duplicate POST for same company and employee returns 400 JOB_ALREADY_ASSIGNED."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "JOB_ALREADY_ASSIGNED"


def test_job_assignments_create_error_6(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """POST when company has no jobs left returns 400 NO_JOB_LEFT."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Bauhof"
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "NO_JOB_LEFT"


def test_job_assignments_create_error_7_effective_schedule_cap(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bauhof_morning_only,
):
    """POST respects ``company_jobs_max`` schedule cap, not only ``companies.jobs_max``."""
    token = _login_as_employee(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "Bauhof",
            "employee_number": "A00265",
            "notes": "Schedule cap exceeded",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    assert response.get_json()["error"] == "NO_JOB_LEFT"


# ---------------------------------------------------------------------
# Deleted job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_delete_ok(client, sample_authentication, sample_company,  sample_employee, sample_job_assignment,): # fmt: skip
    """DELETE by assignment number returns 200 with job deleted message."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    job_assignment_number = create_job_assignment_number(sample_job_assignment.id)
    response = client.delete(
        f"/api/job-assignments/{job_assignment_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "job deleted"


def test_job_assignments_delete_error_1(client, sample_authentication, sample_employee):
    """DELETE with invalid assignment number returns 400 JOB_ASSIGNMENT_NUMBER_WRONG."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    job_assignment_number = "Wrong"
    response = client.delete(
        f"/api/job-assignments/{job_assignment_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "JOB_ASSIGNMENT_NUMBER_WRONG"


def test_job_assignments_delete_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """DELETE with malformed assignment number returns 400 JOB_ASSIGNMENT_NUMBER_WRONG."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    job_assignment_number = "*0000000"
    response = client.delete(
        f"/api/job-assignments/{job_assignment_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "JOB_ASSIGNMENT_NUMBER_WRONG"


def test_job_assignments_delete_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """DELETE with unknown assignment number returns 404 JOB_ASSIGNMENT_NOT_FOUND."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    job_assignment_number = create_job_assignment_number(99999)
    response = client.delete(
        f"/api/job-assignments/{job_assignment_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "JOB_ASSIGNMENT_NOT_FOUND"

# ---------------------------------------------------------------------
# Reset job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_reset_ok(client, sample_authentication, sample_company,  sample_employee, sample_job_assignment,): # fmt: skip
    """Admin POST reset without company_name deletes all assignments and returns count."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "reset successful"
    assert data["count"] == 2

def test_job_assignments_reset_ok_empty(client, sample_authentication, sample_company,  sample_employee, ): # fmt: skip
    """Admin reset for company with no assignments returns count 0."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Bauhof"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "reset successful"
    assert data["count"] == 0

def test_job_assignments_reset_ok_company(client, sample_authentication, sample_company,  sample_employee, sample_job_assignment,): # fmt: skip
    """Admin reset scoped to company_name deletes only that company's assignments."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Bauhof"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "reset successful"
    assert data["count"] == 1

def test_job_assignments_reset_error_1(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    """Admin reset with unknown company returns 404 COMPANY_NOT_FOUND."""
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Wrong"
    response = client.post(
        "/api/job-assignments/reset",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


# ---------------------------------------------------------------------
# Job assignment — attendance check-in gate (POST + DELETE)
# ---------------------------------------------------------------------
KID_JOB_PAYLOAD = {
    "company_name": "Arbeitsamt",
    "employee_number": "M00252",
}

STAFF_JOB_PAYLOAD = {
    "company_name": "Arbeitsamt",
    "employee_number": "A00265",
}


def test_job_assignments_gate_kids_switch_on_blocks_without_check_in(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Kids switch on: POST and DELETE return ATTENDANCE_CHECK_IN_REQUIRED without check-in."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    with patch("app.schemas.attendance.require_attendance_for_kids", return_value=True):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {token}"},
            json=KID_JOB_PAYLOAD,
        )
        if response.status_code != 400:
            print(response.text)
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "ATTENDANCE_CHECK_IN_REQUIRED"

        with patch(
            "app.schemas.attendance.require_attendance_for_kids", return_value=False
        ):
            response = client.post(
                "/api/job-assignments",
                headers={"Authorization": f"Bearer {token}"},
                json=KID_JOB_PAYLOAD,
            )
            if response.status_code != 201:
                print(response.text)
            assert response.status_code == 201
            data = response.get_json()
            kid_job_number = data["job_assignment_number"]

        response = client.delete(
            f"/api/job-assignments/{kid_job_number}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 400:
            print(response.text)
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "ATTENDANCE_CHECK_IN_REQUIRED"


def test_job_assignments_gate_kids_switch_on_succeeds_after_check_in(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Kids switch on: POST and DELETE succeed after today's check-in."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    staff_token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    with patch("app.schemas.attendance.require_attendance_for_kids", return_value=True):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {token}"},
            json=KID_JOB_PAYLOAD,
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201
        data = response.get_json()

        response = client.delete(
            f"/api/job-assignments/{data['job_assignment_number']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200


def test_job_assignments_gate_kids_switch_off_allows_without_check_in(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Kids switch off: create and delete job assignments without check-in."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    with patch(
        "app.schemas.attendance.require_attendance_for_kids", return_value=False
    ):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {token}"},
            json=KID_JOB_PAYLOAD,
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201
        data = response.get_json()

        response = client.delete(
            f"/api/job-assignments/{data['job_assignment_number']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200


def test_job_assignments_gate_staff_switch_off_allows_without_check_in(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Staff switch off: staff POST and admin DELETE proceed without check-in."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    staff_token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip
    with patch(
        "app.schemas.attendance.require_attendance_for_staff", return_value=False
    ):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {staff_token}"},
            json=STAFF_JOB_PAYLOAD,
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201

        admin_job_number = create_job_assignment_number(sample_job_assignment.id)
        response = client.delete(
            f"/api/job-assignments/{admin_job_number}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200


def test_job_assignments_gate_staff_switch_on_blocks_without_check_in(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Staff switch on: POST and DELETE return ATTENDANCE_CHECK_IN_REQUIRED without check-in."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    staff_token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip
    with patch(
        "app.schemas.attendance.require_attendance_for_staff", return_value=True
    ):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {staff_token}"},
            json=STAFF_JOB_PAYLOAD,
        )
        if response.status_code != 400:
            print(response.text)
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "ATTENDANCE_CHECK_IN_REQUIRED"

        admin_job_number = create_job_assignment_number(sample_job_assignment.id)
        response = client.delete(
            f"/api/job-assignments/{admin_job_number}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 400:
            print(response.text)
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "ATTENDANCE_CHECK_IN_REQUIRED"


def test_job_assignments_gate_staff_switch_on_succeeds_after_check_in(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Staff switch on: POST and DELETE succeed after today's check-in."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    staff_token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/attendance/check-in/A00265",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-in/P00370",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    with patch(
        "app.schemas.attendance.require_attendance_for_staff", return_value=True
    ):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {staff_token}"},
            json=STAFF_JOB_PAYLOAD,
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201
        data = response.get_json()

        response = client.delete(
            f"/api/job-assignments/{data['job_assignment_number']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200

        admin_job_number = create_job_assignment_number(sample_job_assignment.id)
        response = client.delete(
            f"/api/job-assignments/{admin_job_number}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200


def test_job_assignments_gate_kid_checked_out_still_allows_post_and_delete(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    camp_today_is_monday,
):
    """Optional check-out does not block job POST/DELETE when today's check-in row exists."""
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip
    staff_token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/attendance/check-in/M00252",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.post(
        "/api/attendance/check-out/M00252",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    with patch("app.schemas.attendance.require_attendance_for_kids", return_value=True):
        response = client.post(
            "/api/job-assignments",
            headers={"Authorization": f"Bearer {token}"},
            json=KID_JOB_PAYLOAD,
        )
        if response.status_code != 201:
            print(response.text)
        assert response.status_code == 201
        data = response.get_json()

        response = client.delete(
            f"/api/job-assignments/{data['job_assignment_number']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200
