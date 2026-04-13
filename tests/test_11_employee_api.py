"""Employee API tests"""

payload_create = {
    "first_name": "Test",
    "last_name": "Created-User",
    "employee_number": "TEST00753",
    "role": "Tester",
    "active": True,
    "notes": "Created by create test",
}

payload_put = {
    "first_name": "Test",
    "last_name": "Created-User",
    "employee_number": "TEST00753",
    "role": "Tester",
    "active": True,
    "notes": "Updated by test",
}

# ---------------------------------------------------------------------
# validate_create_payload function
# ---------------------------------------------------------------------
def test_validate_create_payload_error_1(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/employees", json="{wrong = JSON}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_create_payload_error_2(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={"last_name": "TEST", "employee_number": "TEST", "role": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_3(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={"first_name": "TEST", "employee_number": "TEST", "role": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_4(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={"first_name": "TEST", "last_name": "TEST", "role": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_5(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_6(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={
            "first_name": "",
            "last_name": "TEST",
            "employee_number": "TEST",
            "role": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_7(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={
            "first_name": "TEST",
            "last_name": "",
            "employee_number": "TEST",
            "role": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_8(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "",
            "role": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_9(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees",
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST",
            "role": "",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_create_payload_error_10(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/employees", json={"first_name": "TEST", "last_name": "TEST", "employee_number": "Wrong", "role": "Test"}, # fmt: skip
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


# ---------------------------------------------------------------------
# validate_update_payload function
# ---------------------------------------------------------------------
def test_validate_update_payload_error_1(client, sample_company, sample_employee,): # fmt: skip
    employee_number = sample_employee.employee_number
    response = client.put(f"/api/employees/{employee_number}", json="{wrong = JSON}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

def test_validate_update_payload_error_2(client, sample_company, sample_employee,): # fmt: skip
    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "Wrong"
    employee_number = sample_employee.employee_number
    response = client.put(f"/api/employees/{employee_number}", json=payload_wrong)
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


# ---------------------------------------------------------------------
# Employees  Get-all API
# ---------------------------------------------------------------------
def test_employees_query_all_employees(client, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 3
    assert data["count"] == 3
    assert any(
        employee_data["id"] == sample_employee.id for employee_data in data["employees"]
    )
    assert any(
        employee_data["first_name"] == sample_employee.first_name
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["last_name"] == sample_employee.last_name
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["employee_number"] == sample_employee.employee_number
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["role"] == sample_employee.role
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["active"] is sample_employee.active
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["notes"] == sample_employee.notes
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["company"] == "Bauhof" for employee_data in data["employees"]
    )


def test_employees_query_all_true(client, sample_employee):
    response = client.get("/api/employees?active=true")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 2
    assert data["count"] == 2


def test_employees_query_all_false(client, sample_employee):
    response = client.get("/api/employees?active=false")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 1
    assert data["count"] == 1


def test_employees_query_all_empty(client, db_session,): # fmt: skip
    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 0
    assert data["employees"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------
# Employees Get API
# ---------------------------------------------------------------------
def test_employees_query(client, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    employee_number = sample_employee.employee_number
    response = client.get(f"/api/employees/{employee_number}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 10
    assert data["first_name"] == sample_employee.first_name
    assert data["last_name"] == sample_employee.last_name
    assert data["employee_number"] == sample_employee.employee_number
    assert data["role"] == sample_employee.role
    assert data["active"] is sample_employee.active
    assert data["notes"] == sample_employee.notes
    assert data["company"] == "Bauhof"


def test_employees_query_error_1(client, sample_employee):
    employee_number = "Wrong"
    response = client.get(f"/api/employees/{employee_number}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_employees_query_error_2(client, sample_employee):
    employee_number = "TEST00753"
    response = client.get(f"/api/employees/{employee_number}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


# ---------------------------------------------------------------------
# Employees Create API
# ---------------------------------------------------------------------
def test_employees_create(client, sample_employee): # fmt: skip
    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 3

    response = client.post("/api/employees", json=payload_create)
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201

    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 4


def test_employees_create_error_1(client, sample_employee):
    response = client.post("/api/employees", json=payload_create)
    response = client.post("/api/employees", json=payload_create)
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"


# ---------------------------------------------------------------------
# Employees Update API
# ---------------------------------------------------------------------
def test_employees_update(client, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    employee_number = sample_employee.employee_number
    response = client.put(f"/api/employees/{employee_number}", json=payload_put)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 10
    assert data["first_name"] == payload_put["first_name"]
    assert data["last_name"] == payload_put["last_name"]
    assert data["employee_number"] == payload_put["employee_number"]
    assert data["role"] == payload_put["role"]
    assert data["role"] == payload_put["role"]
    assert data["active"] is payload_put["active"]
    assert data["notes"] == payload_put["notes"]
    assert data["company"] == "Bauhof"

    employee_number = payload_put["employee_number"]
    response2 = client.get(f"/api/employees/{employee_number}")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 10
    assert data2["employee_number"] == payload_put["employee_number"]


def test_employees_update_error_1(client, sample_employee):
    employee_number = "WRONG"
    response = client.put(f"/api/employees/{employee_number}", json=payload_put)
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_employees_update_error_2(client, sample_employee):
    employee_number = "TEST00753"
    response = client.put(f"/api/employees/{employee_number}", json=payload_put)
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


# ---------------------------------------------------------------------
# Employees Delete API
# ---------------------------------------------------------------------
def test_employees_delete_soft(client, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    employee_number = sample_employee.employee_number
    response = client.delete(f"/api/employees/{employee_number}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 10
    assert data["first_name"] == sample_employee.first_name
    assert data["last_name"] == sample_employee.last_name
    assert data["employee_number"] == sample_employee.employee_number
    assert data["role"] == sample_employee.role
    assert data["active"] is not sample_employee.active
    assert data["notes"] == sample_employee.notes
    assert data["company"] == "Bauhof"

    response = client.get(f"/api/employees/{employee_number}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["active"] is not True


def test_employees_delete_hard(client, sample_employee,): # fmt: skip
    employee_number = sample_employee.employee_number
    response = client.delete(f"/api/employees/{employee_number}?hard=true")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "employee deleted permanently"

    response = client.get(f"/api/employees/{employee_number}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404


def test_employees_delete_error_1(client, sample_employee):
    employee_number = "Wrong"
    response = client.delete(f"/api/employees/{employee_number}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_employees_delete_error_2(client, db_session, sample_employee):
    employee_number = "TEST00753"
    response = client.delete(f"/api/job-assignments/{employee_number}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_employees_delete_error_3(client, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    employee_number = sample_employee.employee_number
    response = client.delete(f"/api/employees/{employee_number}?hard=true")
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
