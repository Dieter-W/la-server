"""Company API tests"""

import unicodedata
from urllib.parse import quote

from test_utils import _login_as_admin

payload_create = {
    "company_name": "TEST_COMPANY",
    "jobs_max": 10,
    "hourly_pay": 9,
    "active": True,
    "notes": "Created by create test",
}


payload_put = {
    "company_name": "Kitchen",
    "jobs_max": 5,
    "hourly_pay": 99,
    "active": False,
    "notes": "Updated by test",
}


def _nfc(s: str) -> str:
    """Normalize Unicode so DB round-trips match Python string literals (NFC vs NFD)."""
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------
# validate_create_payload function
# ---------------------------------------------------------------------
def test_validate_create_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    data = response.get_json()
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_create_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"jobs_max": "TEST", "hourly_pay": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "TEST", "hourly_pay": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "TEST", "jobs_max": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_5(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "", "jobs_max": "TEST", "hourly_pay": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_6(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "TEST", "jobs_max": "", "hourly_pay": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_7(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "TEST", "jobs_max": "TEST", "hourly_pay": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


# ---------------------------------------------------------------------
# validate_update_payload function
# ---------------------------------------------------------------------
def test_validate_update_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    company_name = sample_company.company_name
    response = client.put(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


# ---------------------------------------------------------------------
# Company Get-all API
# ---------------------------------------------------------------------
def test_companies_query_all(client, sample_company, sample_job_assignment): # fmt: skip
    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 4
    assert data["count"] == 4
    assert any(
        company_data["id"] == sample_company.id for company_data in data["companies"]
    )
    assert any(
        _nfc(company_data["company_name"]) == _nfc(sample_company.company_name)
        for company_data in data["companies"]
    )
    assert any(
        company_data["jobs"]["max"] == sample_company.jobs_max
        for company_data in data["companies"]
    )
    assert any(
        company_data["jobs"]["available"] == 0 for company_data in data["companies"]
    )
    assert any(
        company_data["hourly_pay"] == sample_company.hourly_pay
        for company_data in data["companies"]
    )
    assert any(
        company_data["active"] == sample_company.active
        for company_data in data["companies"]
    )
    assert any(
        company_data["notes"] == sample_company.notes
        for company_data in data["companies"]
    )


def test_companies_query_all_true(client, sample_company, ): # fmt: skip
    response = client.get("/api/companies?active=true")
    if response.status_code != 200:
        print(response.text)
    data = response.get_json()
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 3
    assert data["count"] == 3


def test_companies_query_all_false(client, sample_company,): # fmt: skip
    response = client.get("/api/companies?active=false")
    if response.status_code != 200:
        print(response.text)
    data = response.get_json()
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 1
    assert data["count"] == 1


def test_companies_query_all_empty(client, db_session,): # fmt: skip
    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    data = response.get_json()
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 0
    assert data["companies"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------
# Company Get API
# ---------------------------------------------------------------------
def test_companies_query(client, sample_company, sample_job_assignment,): # fmt: skip
    company_name = sample_company.company_name
    response = client.get(f"/api/companies/{quote(company_name, safe='')}")
    if response.status_code != 200:
        print(response.text)
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 8
    assert data["company_name"] == sample_company.company_name
    assert data["jobs"]["available"] == 0
    assert data["jobs"]["max"] == sample_company.jobs_max
    assert data["hourly_pay"] == sample_company.hourly_pay
    assert data["active"] is sample_company.active
    assert data["notes"] == sample_company.notes


def test_companies_query_error_1(client, sample_company, sample_job_assignment,): # fmt: skip
    company_name = "Wrong"
    response = client.get(f"/api/companies/{quote(company_name, safe='')}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


# ---------------------------------------------------------------------
# Company Create API
# ---------------------------------------------------------------------
def test_companies_create(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 4

    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 8
    assert data["company_name"] == payload_create["company_name"]
    assert data["jobs"]["available"] == payload_create["jobs_max"]
    assert data["jobs"]["max"] == payload_create["jobs_max"]
    assert data["hourly_pay"] == payload_create["hourly_pay"]
    assert data["active"] == payload_create["active"]
    assert data["notes"] == payload_create["notes"]

    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 5


def test_companies_create_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    # Post /api/companies
    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    response = client.post(
        "/api/companies",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
    assert data["message"] == "Create failed, because entry is already in database"


# ---------------------------------------------------------------------
# Company Update API
# ---------------------------------------------------------------------
def test_companies_update(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    company_name = sample_company.company_name
    response = client.put(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    if response.status_code != 200:
        print(response.text)
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 8
    assert data["id"] == sample_company.id
    assert _nfc(data["company_name"]) == _nfc(payload_put["company_name"])
    assert data["hourly_pay"] == payload_put["hourly_pay"]
    assert data["active"] == payload_put["active"]
    assert data["notes"] == payload_put["notes"]

    response2 = client.get("/api/companies/Kitchen")
    if response.status_code != 200:
        print(response.text)
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 8
    assert data2["company_name"] == payload_put["company_name"]


def test_companies_update_error_1(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    company_name = "Wrong"
    response = client.put(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_companies_update_error_2_duplicate_name(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    """PUT rename collides with another company's unique company_name -> 409."""
    response = client.put(
        f"/api/companies/{quote('Bank', safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Küche"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
    assert data["message"] == "Create failed, because entry is already in database"


# ---------------------------------------------------------------------
# Company Delete API
# ---------------------------------------------------------------------
def test_companies_delete(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    company_name = sample_company.company_name
    response = client.delete(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    data = response.get_json()
    assert isinstance(data, dict)
    assert data["message"] == "company deleted permanently"

    response = client.get(f"/api/companies/{quote(company_name, safe='')}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404


def test_companies_delete_error_1(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    company_name = "Wrong"
    response = client.delete(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "COMPANY_NOT_FOUND"


def test_companies_delete_Error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    company_name = sample_company.company_name
    response = client.delete(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
    assert data["message"] == "Delete failed, because related entries in JobAssignment table" # fmt: skip
