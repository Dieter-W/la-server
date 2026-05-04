"""Authentication API tests"""

from test_utils import (
    _login_as_admin,
    _login_as_employee,
    _login_as_staff,
    _login_as_employee_expired_token,
    _login_as_employee_expired_refresh_token,
    _get_refresh_token,
)

# ---------------------------------------------------------------------
# validate_create_payload function
# ---------------------------------------------------------------------
def test_validate_authenticate_payload_error_1(client, sample_company, sample_employee,): # fmt: skip
    response = client.post("/api/auth/login", json="{wrong = JSON}")
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_authenticate_payload_error_2(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={
            "employee_number": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_authenticate_payload_error_3(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"password": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_authenticate_payload_error_4(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "", "password": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_authenticate_payload_error_5(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "TEST", "password": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_authenticate_payload_error_6(client, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "Wrong", "password": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


# ---------------------------------------------------------------------
# validate_set_password_payload function
# ---------------------------------------------------------------------
def test_validate_set_auth_group_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )
    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_set_auth_group_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_number": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_set_auth_group_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={"auth_group": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400


def test_validate_set_auth_group_payload_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "", "auth_group": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_set_auth_group_payload_error_5(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "TEST", "auth_group": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400

def test_validate_set_auth_group_payload_error_6(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )
    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "Wrong", "auth_group": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"

def test_validate_set_auth_group_payload_error_7(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(
        client,
        sample_authentication,
        sample_employee,
    )

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_number": "TEST00753",
            "auth_group": "Wrong",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "INVALID_AUTH_GROUP_IN_JSON"

# ---------------------------------------------------------------------
# validate_set_password_payload function
# ---------------------------------------------------------------------
def test_validate_set_password_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(
        client,
        sample_authentication,
        sample_employee,
    )
    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_set_password_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_password": "TEST"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_set_password_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_password": "", "old_password": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400


def test_validate_set_password_payload_error_5(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_password": "TEST", "old_password": ""},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_reset_password_payload_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json="{wrong = JSON}",
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"


def test_validate_reset_password_payload_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "last_name": "TEST",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_reset_password_payload_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_number": "",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"


def test_validate_reset_password_payload_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "Wrong"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NUMBER_WRONG_IN_JSON"


# ---------------------------------------------------------------------
# Authentication Login API
# ---------------------------------------------------------------------
def test_authenticate_as_employee_ok(client, sample_authentication, sample_employee,): # fmt: skip
    _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

def test_authenticate_as_staff_ok(client, sample_authentication,sample_employee,): # fmt: skip
    _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

def test_authenticate_as_admin_ok(client, sample_authentication,sample_employee,): # fmt: skip
    _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip


def test_authenticate_error_1(client, sample_authentication,sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "TEST00753", "password": "Created-User"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

def test_authenticate_error_2(client, sample_authentication,sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "M00155", "password": "Mustermann"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"

def test_authenticate_error_3(client, sample_authentication,sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "M00252", "password": "Wrong"},
    )
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "BAD_CREDENTIALS"


# ---------------------------------------------------------------------
# Authentication ME API
# ---------------------------------------------------------------------
def test_me_as_employee_ok(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "M00252"
    assert data["auth_group"] == "employee"


def test_me_as_staff_ok(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == "A00265"
    assert data["auth_group"] == "staff"

def test_me_as_admin_ok(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["employee_number"] == sample_employee.employee_number
    assert data["first_name"] == sample_employee.first_name
    assert data["last_name"] == sample_employee.last_name
    assert data["employee_number"] == sample_employee.employee_number
    assert data["role"] == sample_employee.role
    assert data["active"] is sample_employee.active
    assert data["notes"] == sample_employee.notes
    assert data["auth_group"] == "admin"
    assert data["company"] == "Bauhof"
    assert data["auth_group"] == "admin"

def test_me_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}-invalid-token"},
    )
    if response.status_code != 422:
        print(response.text)
    assert response.status_code == 422
    data = response.get_json()
    assert data["error"] == "INVALID_TOKEN"
    assert data["message"] == "Invalid crypto padding"

def test_me_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token_admin = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    token_staff = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "A00265"
    response = client.delete(
        f"/api/employees/{employee_number}?hard=true",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_staff}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

def test_me_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token_admin = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    token_staff = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "A00265"
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"active": False},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_staff}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"


def test_me_error_4(client, sample_authentication, sample_employee,):  # fmt: skip
    token = _login_as_employee_expired_token(client)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "EXPIRED_TOKEN"
    assert data["message"] == "Token has expired"


# ---------------------------------------------------------------------
# Authentication Set Auth Group API
# ---------------------------------------------------------------------
def test_set_auth_group_ok(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_number": "A00265",
            "auth_group": "employee",
        },
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Auth group set"
    assert data["auth_group"] == "employee"
    assert data["employee_number"] == "A00265"


def test_set_auth_group_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}-invalid-token"},
        json={
            "employee_number": "A00265",
            "auth_group": "employee",
        },
    )
    if response.status_code != 422:
        print(response.text)
    assert response.status_code == 422
    data = response.get_json()
    assert data["error"] == "INVALID_TOKEN"
    assert data["message"] == "Invalid crypto padding"


def test_set_auth_group_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token= _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "Test00753"
    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_number": employee_number,
            "auth_group": "employee",
        },
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"


def test_set_auth_group_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "A00265"
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token}"},
        json={"active": False},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/auth/set-auth-group",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_number": employee_number,
            "auth_group": "employee",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"


# ---------------------------------------------------------------------
# Authentication Set Password API
# ---------------------------------------------------------------------
def test_set_password_ok(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_password": "Test", "old_password": "Schmidt"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Password set"

def test_set_password_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}-invalid-token"},
        json={"new_password": "Test", "old_password": "Schmidt"},
    )
    if response.status_code != 422:
        print(response.text)
    assert response.status_code == 422
    data = response.get_json()
    assert data["error"] == "INVALID_TOKEN"
    assert data["message"] == "Invalid crypto padding"

def test_set_password_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token_admin = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    token_staff = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "A00265"
    response = client.delete(
        f"/api/employees/{employee_number}?hard=true",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token_staff}"},
        json={"new_password": "Test", "old_password": "Schmidt"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

def test_set_password_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token_admin = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    token_staff = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "A00265"
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"active": False},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token_staff}"},
        json={"new_password": "Test", "old_password": "Schmidt"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"

def test_set_password_error_4(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/set-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_password": "Test", "old_password": "Wrong"},
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "OLD_PASSWORD_IS_INCORRECT"

# ---------------------------------------------------------------------
# Authentication Reset Password API
# ---------------------------------------------------------------------
def test_reset_password_ok(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "A00265"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Password reset"

def test_reset_password_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}-invalid-token"},
        json={"employee_number": "A00265"},
    )
    if response.status_code != 422:
        print(response.text)
    assert response.status_code == 422
    data = response.get_json()
    assert data["error"] == "INVALID_TOKEN"
    assert data["message"] == "Invalid crypto padding"

def test_reset_password_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip

    employee_number = "A00265"
    response = client.delete(
        f"/api/employees/{employee_number}?hard=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "A00265"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

# ---------------------------------------------------------------------
# Authentication Refresh Token API
# ---------------------------------------------------------------------
def test_refresh_token_ok(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    refresh_token = _get_refresh_token(client, "M00252", "Mustermann")

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Token refreshed"
    assert data["token"] is not None


def test_refresh_token_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    refresh_token = _get_refresh_token(client, "M00252", "Mustermann")

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}-invalid-token"},
    )
    if response.status_code != 422:
        print(response.text)
    assert response.status_code == 422
    data = response.get_json()
    assert data["error"] == "INVALID_TOKEN"
    assert data["message"] == "Invalid crypto padding"

def test_refresh_token_error_2(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token_admin = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    refresh_token_employee = _get_refresh_token(client, "M00252", "Mustermann")

    employee_number = "M00252"
    response = client.delete(
        f"/api/employees/{employee_number}?hard=true",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token_employee}"},
    )
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_FOUND"

def test_refresh_token_error_3(client, sample_authentication, sample_company, sample_employee, sample_job_assignment,): # fmt: skip
    token_admin = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    refresh_token_employee = _get_refresh_token(client, "M00252", "Mustermann")

    employee_number = "M00252"
    response = client.put(
        f"/api/employees/{employee_number}",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"active": False},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token_employee}"},
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "EMPLOYEE_NOT_ACTIVE"


def test_refresh_token_error_4(client, sample_authentication, sample_employee,):  # fmt: skip
    token = _login_as_employee_expired_refresh_token(client)

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "EXPIRED_TOKEN"
    assert data["message"] == "Token has expired"


# ---------------------------------------------------------------------
# Authentication Logout API
# ---------------------------------------------------------------------
def test_logout_ok(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Logged out"
    assert data["token"] is not None

# ---------------------------------------------------------------------
# Authentication level checks
# ---------------------------------------------------------------------
def test_auth_level_error_1(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    response = client.post(
        "/api/auth/password/reset-password",
        json={"employee_number": "A00265"},
    )
    if response.status_code != 401:
        print(response.text)
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "AUTHORIZATION_REQUIRED"
    assert data["message"] == "Missing Authorization Header"

def test_auth_level_error_2(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.post(
        "/api/auth/password/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_number": "A00265"},
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"

def test_auth_level_error_3(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_employee(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get(
        "/api/health/runtime",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"


def test_auth_level_error_4(client, sample_authentication, sample_company, sample_employee,): # fmt: skip
    token = _login_as_staff(client, sample_authentication, sample_employee,) # fmt: skip

    response = client.get(
        "/api/health/runtime",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 403:
        print(response.text)
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "FORBIDDEN_WRONG_AUTH_GROUP"
