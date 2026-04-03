"""Company API tests"""

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


def test_query_all_employees(client, sample_employee):
    # Get /api/employees
    response = client.get("/api/employees")
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
        employee_data["active"] == sample_employee.active
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["notes"] == sample_employee.notes
        for employee_data in data["employees"]
    )


def test_query_all_employees_true(client, sample_employee):
    # Get /api/employees?active=true
    response = client.get("/api/employees?active=true")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 2
    assert data["count"] == 2


def test_query_all_employees_false(client, sample_employee):
    # Get /api/employees?active=false
    response = client.get("/api/employees?active=false")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 1
    assert data["count"] == 1


def test_query_all_employees_empty(
    client,
    db_session,
):
    # Get /api/employees
    response = client.get("/api/employees")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 0
    assert data["employees"] == []
    assert data["count"] == 0


def test_query_employee(client, sample_employee):
    # Get /api/employees/<employee_number>
    employee_number = sample_employee.employee_number
    response = client.get(f"/api/employees/{employee_number}")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert data["employee_number"] == sample_employee.employee_number


def test_create_employee(client, sample_employee):
    # Post /api/employees
    response = client.post("/api/employees", json=payload_create)
    assert response.status_code == 201
    data = response.get_json()
    assert isinstance(data, dict)


def test_create_employee_wrong_checksum(client, sample_employee):
    # Post /api/employees
    payload_wrong = payload_create.copy()
    payload_wrong["employee_number"] = "Wrong"
    response = client.post("/api/employees", json=payload_wrong)
    assert response.status_code == 400
    data = response.get_json()
    assert isinstance(data, dict)


def test_create_employee_duplicate(client, sample_employee):
    # Post /api/employees
    response = client.post("/api/employees", json=payload_create)
    response = client.post("/api/employees", json=payload_create)
    assert response.status_code == 409


def test_update_employee(client, db_session, sample_employee):
    # Put /api/employee/<employee_number>
    employee_number = sample_employee.employee_number
    response = client.put(f"/api/employees/{employee_number}", json=payload_put)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 9
    assert data["id"] == sample_employee.id
    assert data["first_name"] == payload_put["first_name"]
    assert data["last_name"] == payload_put["last_name"]
    assert data["employee_number"] == payload_put["employee_number"]
    assert data["role"] == payload_put["role"]
    assert data["active"] == payload_put["active"]
    assert data["notes"] == payload_put["notes"]

    employee_number = payload_put["employee_number"]
    response2 = client.get(f"/api/employees/{employee_number}")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 9
    assert data2["employee_number"] == payload_put["employee_number"]


def test_delete_employee_soft(client, sample_employee):
    # Delete /api/employees/<employee_number>
    employee_number = sample_employee.employee_number
    response = client.delete(f"/api/employees/{employee_number}")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert data["active"] is not True
    response = client.get(f"/api/employees/{employee_number}")
    assert response.status_code == 200
    assert data["active"] is not True


def test_delete_employee_hard(client, db_session, sample_employee):
    # Delete /api/employees/<employee_number>?hard=true
    employee_number = sample_employee.employee_number
    response = client.delete(f"/api/employees/{employee_number}?hard=true")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    response = client.get(f"/api/employees/{employee_number}")
    assert response.status_code == 404
