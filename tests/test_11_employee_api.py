"""Employee API tests"""

from tests.test_utils import _login_as_admin

payload_create = {
    "first_name": "Test",
    "last_name": "Created-User",
    "employee_number": "TEST00753",
    "age": 21,
    "can_leave_alone": True,
    "role": "Tester",
    "active": True,
    "notes": "Created by create test",
    "auth_group": "employee",
}

payload_put = {
    "first_name": "Test",
    "last_name": "Created-User",
    "employee_number": "TEST00753",
    "age": 22,
    "can_leave_alone": True,
    "role": "Tester",
    "active": True,
    "notes": "Updated by test",
}

# ---------------------------------------------------------------------
# POST /employees — invalid payload
# ---------------------------------------------------------------------
def test_employees_create_invalid_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_employees_create_invalid_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "last_name": "TEST",
            "employee_number": "TEST",
            "role": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "employee_number": "TEST",
            "role": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "role": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_5(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"

def test_employees_create_invalid_payload_error_6(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
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

def test_employees_create_invalid_payload_error_7(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "",
            "last_name": "TEST",
            "employee_number": "TEST",
            "role": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_8(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "",
            "employee_number": "TEST",
            "role": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_9(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "",
            "role": "TEST",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_10(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST",
            "role": "",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_11(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST",
            "role": "TEST",
            "auth_group": "",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_employees_create_invalid_payload_error_12(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "Wrong",
            "age": 21,
            "role": "Test",
            "auth_group": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


def test_employees_create_invalid_payload_error_13(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST00753",
            "age": 21,
            "role": "Test",
            "auth_group": "Wrong",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_AUTH_GROUP_IN_JSON"


def test_employees_create_invalid_payload_error_14(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST00753",
            "age": True,
            "role": "Test",
            "auth_group": "employee",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_AGE_IN_JSON"


def test_employees_create_invalid_payload_error_15(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST00753",
            "age": -1,
            "role": "Test",
            "auth_group": "employee",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_AGE_IN_JSON"


def test_employees_create_invalid_payload_error_16(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST00753",
            "age": "not-a-number",
            "role": "Test",
            "auth_group": "employee",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_AGE_IN_JSON"


def test_employees_create_invalid_payload_error_17(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST00753",
            "age": 21,
            "role": "Test",
            "auth_group": "employee",
            "can_leave_alone": "maybe",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_JSON_BOOLEAN_IN_JSON"


def test_employees_create_invalid_payload_error_18(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "TEST",
            "last_name": "TEST",
            "employee_number": "TEST00753",
            "age": 21,
            "role": "Test",
            "auth_group": "employee",
            "active": 2,
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_JSON_BOOLEAN_IN_JSON"


# ---------------------------------------------------------------------
# PUT /employees — invalid payload
# ---------------------------------------------------------------------
def test_employees_update_invalid_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"

def test_employees_update_invalid_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "Wrong"
    employee_number = sample_employee.employee_number
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_wrong,
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


def test_employees_update_invalid_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json={"age": True},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_AGE_IN_JSON"


def test_employees_update_invalid_payload_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json={"can_leave_alone": 2},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_JSON_BOOLEAN_IN_JSON"


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
    assert len(data["employees"]) == 4
    assert data["count"] == 4
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
        employee_data["age"] == sample_employee.age
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["can_leave_alone"] is sample_employee.can_leave_alone
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
    assert all(
        employee_data["full_time"] is True for employee_data in data["employees"]
    )


def test_employees_query_all_true(client, sample_employee):
    response = client.get("/api/employees?active=true")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 3
    assert data["count"] == 3


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
    assert len(data) == 13
    assert data["full_time"] is True
    assert data["first_name"] == sample_employee.first_name
    assert data["last_name"] == sample_employee.last_name
    assert data["employee_number"] == sample_employee.employee_number
    assert data["age"] == sample_employee.age
    assert data["can_leave_alone"] is sample_employee.can_leave_alone
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
def test_employees_create(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 4

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    created = response.get_json()
    assert created["auth_group"] == payload_create["auth_group"]
    assert created["age"] == payload_create["age"]
    assert created["can_leave_alone"] is payload_create["can_leave_alone"]

    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 5

    response = client.post(
        "/api/auth/login",
        json={"employee_number": "TEST00753", "password": "Created-User"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Authenticated"
    assert data["token"] is not None
    assert data["auth_group"] == "employee"
    assert data["password_must_change"] is True


def test_employees_create_json_age_string_integer(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "first_name": "String",
            "last_name": "Age",
            "employee_number": "TEMP00987",
            "age": "19",
            "can_leave_alone": 0,
            "role": "Tester",
            "active": "yes",
            "notes": "age as JSON string; bool-like fields",
            "auth_group": "employee",
        },
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
    data = response.get_json()
    assert data["age"] == 19
    assert data["can_leave_alone"] is False
    assert data["active"] is True


def test_employees_create_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    response = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_create,
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
    assert data["message"] == "Create failed, because entry is already in database"  # fmt: skip


# ---------------------------------------------------------------------
# Employees Update API
# ---------------------------------------------------------------------
def test_employees_update(client, sample_authentication, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 13
    assert data["first_name"] == payload_put["first_name"]
    assert data["last_name"] == payload_put["last_name"]
    assert data["employee_number"] == payload_put["employee_number"]
    assert data["age"] == payload_put["age"]
    assert data["can_leave_alone"] is payload_put["can_leave_alone"]
    assert data["role"] == payload_put["role"]
    assert data["active"] is payload_put["active"]
    assert data["notes"] == payload_put["notes"]
    assert data["company"] == "Bauhof"

    employee_number = payload_put["employee_number"]
    response2 = client.get(f"/api/employees/{employee_number}")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 13
    assert data2["employee_number"] == payload_put["employee_number"]


def test_employees_update_partial_json_active_false(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json={"active": False},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["active"] is False
    assert data["employee_number"] == employee_number


def test_employees_update_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = "WRONG"
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_employees_update_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = "TEST00753"
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_employees_update_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    """PUT changes employee_number to one that already exists -> 409."""
    response = client.put(
        "/api/employees/M00155",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "A00265"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
    assert data["message"] == "Create failed, because entry is already in database"


# ---------------------------------------------------------------------
# Employees Delete API
# ---------------------------------------------------------------------
def test_employees_delete_soft(client, sample_authentication, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.delete(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 13
    assert data["first_name"] == sample_employee.first_name
    assert data["last_name"] == sample_employee.last_name
    assert data["employee_number"] == sample_employee.employee_number
    assert data["age"] == sample_employee.age
    assert data["can_leave_alone"] is sample_employee.can_leave_alone
    assert data["role"] == sample_employee.role
    assert data["active"] is not sample_employee.active
    assert data["notes"] == sample_employee.notes
    assert data["company"] == "Bauhof"

    response = client.get(f"/api/employees/{employee_number}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["active"] is not True


def test_employees_delete_hard(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.delete(
        f"/api/employees/{employee_number}?hard=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "employee deleted permanently"

    response = client.get(f"/api/employees/{employee_number}")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404


def test_employees_delete_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = "Wrong"
    response = client.delete(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG"


def test_employees_delete_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = "TEST00753"
    response = client.delete(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_employees_delete_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    employee_number = sample_employee.employee_number
    response = client.delete(
        f"/api/employees/{employee_number}?hard=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 409:
        print(response.text)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONSTRAINT_VIOLATION"
    assert (
        data["message"]
        == "Delete failed, because related entries in JobAssignment table"
    )


# ---------------------------------------------------------------------
# Employees — full_time (part_times)
# ---------------------------------------------------------------------
def test_employees_full_time_false_when_part_times_exist(
    client,
    app,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    from app.models import PartTime

    with app.app_context():
        session = app.SessionLocal()
        session.add(PartTime(employee_id=2, workday="monday", shift="morning"))
        session.commit()
        session.close()

    response = client.get("/api/employees/M00252")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.get_json()["full_time"] is False

    response = client.get("/api/employees")
    assert response.status_code == 200
    monika = next(
        e for e in response.get_json()["employees"] if e["employee_number"] == "M00252"
    )
    assert monika["full_time"] is False
