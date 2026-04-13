"""Company API tests"""

import unicodedata

# from urllib.parse import quote

payload_create = {
    "company_name": "Arbeitsamt",
    "employee_number": "A00265",
    "notes": "Created by create test",
}


payload_put = {
    "company_name": "Kitchen",
    "jobs_max": 5,
    "pay_per_hour": 99,
    "active": False,
    "notes": "Updated by test",
}


def _nfc(s: str) -> str:
    """Normalize Unicode so DB round-trips match Python string literals (NFC vs NFD)."""
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------
# validate_create_payload function
# ---------------------------------------------------------------------
def test_validate_create_payload_error_1(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/job-assignments", json="{wrong = JSON}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_create_payload_error_2(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/job-assignments", json={"employee_number": "Test"})
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_3(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/job-assignments", json={"company_name": "Test"})
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_4(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/job-assignments", json={"company_name": "", "employee_number": "Test"}
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_5(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/job-assignments", json={"company_name": "Test", "employee_number": ""}
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_6(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/job-assignments", json={"company_name": "Test", "employee_number": "Wrong"}, # fmt: skip
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


# ---------------------------------------------------------------------
# validate_reset_payload function
# ---------------------------------------------------------------------
def test_validate_reset_payload_error_1(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/job-assignments/reset", json="{wrong = JSON}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_reset_payload_error_2(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/job-assignments/reset", json={"test": "test"})
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_reset_payload_error_3(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/job-assignments/reset", json={"company_name": ""})
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


# ---------------------------------------------------------------------
# Get-all job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_get_ok(client, sample_company, sample_employee, sample_job_assignment,):  # fmt: skip
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
def test_job_assignments_create_ok(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    response = client.get("/api/job-assignments")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2

    response = client.post("/api/job-assignments", json=payload_create)
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/job-assignments")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 3

def test_job_assignments_create_error_1(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Wrong"
    response = client.post("/api/job-assignments", json=payload_wrong)
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_job_assignments_create_error_2(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Bank"
    response = client.post("/api/job-assignments", json=payload_wrong)
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_ACTIVE"


def test_job_assignments_create_error_3(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "TEST00753"
    response = client.post("/api/job-assignments", json=payload_wrong)
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404

    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

def test_job_assignments_create_error_4(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "M00155"
    response = client.post("/api/job-assignments", json=payload_wrong)
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"


def test_job_assignments_create_error_5(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    response = client.post("/api/job-assignments", json=payload_create)
    assert response.status_code == 201

    response = client.post("/api/job-assignments", json=payload_create)
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "JOB_ALREADY_ASSIGNED"


def test_job_assignments_create_error_6(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Bauhof"
    response = client.post("/api/job-assignments", json=payload_wrong)
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "NO_JOB_LEFT"


# ---------------------------------------------------------------------
# Deleted job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_delete_ok(client, sample_company,  sample_employee, sample_job_assignment,): # fmt: skip
    employee_number = "M00155"
    response = client.delete(f"/api/job-assignments/{employee_number}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "job deleted"


def test_job_assignments_delete_error_1(client, sample_employee):
    employee_number = "Wrong"
    response = client.delete(f"/api/job-assignments/{employee_number}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_job_assignments_delete_error_2(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    employee_number = "TEST00753"
    response = client.delete(f"/api/job-assignments/{employee_number}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_job_assignments_delete_error_3(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    employee_number = "A00265"
    response = client.delete(f"/api/job-assignments/{employee_number}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "NO_JOB_ASSIGNED"


# ---------------------------------------------------------------------
# Reset job_assignment API
# ---------------------------------------------------------------------
def test_job_assignments_reset_ok(client, sample_company,  sample_employee, sample_job_assignment,): # fmt: skip
    response = client.post("/api/job-assignments/reset")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "reset successful"
    assert data["count"] == 2

def test_job_assignments_reset_ok_empty(client, sample_company,  sample_employee, ): # fmt: skip
    response = client.post("/api/job-assignments/reset", json={"company_name": "Bauhof"}) # fmt: skip
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "reset successful"
    assert data["count"] == 0

def test_job_assignments_reset_ok_company(client, sample_company,  sample_employee, sample_job_assignment,): # fmt: skip
    response = client.post("/api/job-assignments/reset", json={"company_name": "Bauhof"}) # fmt: skip
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "reset successful"
    assert data["count"] == 1

def test_job_assignments_reset_error_1(client, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["company_name"] = "Wrong"
    response = client.post("/api/job-assignments/reset", json=payload_wrong)
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"
