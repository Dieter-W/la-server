"""Helpers for JWT login and token fixtures used by API tests."""

import unicodedata
from datetime import timedelta

from flask_jwt_extended import create_access_token, create_refresh_token


# ---------------------------------------------------------------------
# Unicode — normalize for DB round-trip comparisons
# ---------------------------------------------------------------------
def nfc(s: str) -> str:
    """Normalize Unicode so DB round-trips match Python string literals (NFC vs NFD)."""
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------
# Login — shared POST /api/auth/login helper
# ---------------------------------------------------------------------
def _login(
    client,
    employee_number: str,
    password: str,
    *,
    auth_group: str,
    password_must_change: bool,
) -> str:
    """POST /api/auth/login; return access token after asserting response."""
    response = client.post(
        "/api/auth/login",
        json={"employee_number": employee_number, "password": password},
    )
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Authenticated"
    assert data["token"] is not None
    assert data["refresh_token"] is not None
    assert data["auth_group"] == auth_group
    assert data["password_must_change"] is password_must_change
    return data["token"]


# ---------------------------------------------------------------------
# Login — employee access token (seeded M00252)
# ---------------------------------------------------------------------
def _login_as_employee(client, sample_authentication=None, sample_employee=None) -> str:  # fmt: skip
    """POST /api/auth/login as seeded employee ``M00252``; return access ``token``."""
    return _login(
        client,
        "M00252",
        "Mustermann",
        auth_group="employee",
        password_must_change=True,
    )


# ---------------------------------------------------------------------
# Login — staff access token (seeded A00265)
# ---------------------------------------------------------------------
def _login_as_staff(client, sample_authentication=None, sample_employee=None) -> str:  # fmt: skip
    """POST /api/auth/login as seeded staff ``A00265``; return access ``token``."""
    return _login(
        client,
        "A00265",
        "Schmidt",
        auth_group="staff",
        password_must_change=False,
    )


# ---------------------------------------------------------------------
# Login — admin access token (seeded P00370)
# ---------------------------------------------------------------------
def _login_as_admin(client, sample_authentication=None, sample_employee=None) -> str:  # fmt: skip
    """POST /api/auth/login as seeded admin ``P00370``; return access ``token``."""
    return _login(
        client,
        "P00370",
        "Krause",
        auth_group="admin",
        password_must_change=True,
    )


# ---------------------------------------------------------------------
# Login — arbitrary user refresh token
# ---------------------------------------------------------------------
def _get_refresh_token(client, employee_number: str, password: str) -> str:
    """Log in and return the refresh token."""
    response = client.post(
        "/api/auth/login",
        json={"employee_number": employee_number, "password": password},
    )
    assert response.status_code == 200
    return response.get_json()["refresh_token"]


# ---------------------------------------------------------------------
# Fixture — expired access token (auth id 2 / M00252)
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# Fixture — expired refresh token (auth id 2 / M00252)
# ---------------------------------------------------------------------
def _login_as_employee_expired_refresh_token(client) -> str:
    """Expired refresh token for auth id 2 (M00252)."""
    with client.application.app_context():
        return create_refresh_token(
            identity="2",
            additional_claims={
                "auth_group": "employee",
                "employee_number": "M00252",
            },
            expires_delta=timedelta(seconds=-1),
        )
