"""Utility functions for authentication tests"""

from datetime import timedelta
from flask_jwt_extended import create_access_token

# ---------------------------------------------------------------------
# Login as employee, staff, admin functions
# ---------------------------------------------------------------------
def _login_as_employee(client, sample_authentication, sample_employee,) -> str: # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "M00252", "password": "Mustermann"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Authenticated"
    assert data["token"] is not None
    assert data["auth_group"] == "employee"
    assert data["password_must_change"] is True

    return data["token"]

def _login_as_staff(client, sample_authentication, sample_employee,) -> str: # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "A00265", "password": "Schmidt"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Authenticated"
    assert data["token"] is not None
    assert data["auth_group"] == "staff"
    assert data["password_must_change"] is False

    return data["token"]

def _login_as_admin(client, sample_authentication, sample_employee,) -> str: # fmt: skip
    response = client.post(
        "/api/auth/login",
        json={"employee_number": "P00370", "password": "Krause"},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Authenticated"
    assert data["token"] is not None
    assert data["auth_group"] == "admin"
    assert data["password_must_change"] is False

    return data["token"]


def _login_as_employee_expired_token(client) -> str:
    """Access token for auth id 2 (M00252) that is already expired."""
    with client.application.app_context():
        return create_access_token(
            identity="2",
            additional_claims={
                "auth_group": "employee",
                "employee_number": "M00252",
            },
            expires_delta=timedelta(seconds=-1),
        )
