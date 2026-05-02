"""Bulk insert/update employees and validate them with an API call"""

import sys
import subprocess

import unicodedata
from pathlib import Path
from urllib.parse import quote

from test_utils import _login_as_admin

_REPO_ROOT = Path(__file__).resolve().parents[1]

employee_check = {
    "first_name": "Peter",
    "last_name": "Krause",
    "employee_number": "P00370",
    "role": "Leiter",
    "active": True,
    "notes": "Team lead",
}

payload_put = {
    "first_name": "Test",
    "last_name": "Created-User",
    "role": "Tester",
    "active": False,
    "notes": "Updated by test",
}


def _nfc(s: str) -> str:
    """Normalize Unicode so DB round-trips match Python string literals (NFC vs NFD)."""
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------
# Employees bulk import with API check
# ---------------------------------------------------------------------
def test_bulk_import_employees_create(client,): # fmt: skip
    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stderr

    # Query all
    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 4
    assert data["count"] == 4

    by_number = {e["employee_number"]: e for e in data["employees"]}
    peter = by_number[employee_check["employee_number"]]
    assert _nfc(peter["first_name"]) == _nfc(employee_check["first_name"])
    assert _nfc(peter["last_name"]) == _nfc(employee_check["last_name"])
    assert _nfc(peter["role"]) == _nfc(employee_check["role"])
    assert peter["active"] is employee_check["active"]
    assert peter["notes"] == employee_check["notes"]


# ---------------------------------------------------------------------
# Employees bulk update with API check
# ---------------------------------------------------------------------
def test_bulk_import_employees_update(client,): # fmt: skip

    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stderr

    # Update the bulk input ...
    token = _login_as_admin(
        client,
    )

    employee_number = employee_check["employee_number"]
    response = client.put(
        f"/api/employees/{quote(employee_number, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )

    # and check if update was successful
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 10
    assert _nfc(data["first_name"]) == _nfc(payload_put["first_name"])
    assert _nfc(data["last_name"]) == _nfc(payload_put["last_name"])
    assert _nfc(data["role"]) == _nfc(payload_put["role"])
    assert data["active"] is payload_put["active"]
    assert _nfc(data["notes"]) == _nfc(payload_put["notes"])

    # In place update, with original data
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stderr

    # Check if the original content again available
    employee_number = employee_check["employee_number"]
    response2 = client.get(f"/api/employees/{quote(employee_number, safe='')}")
    if response2.status_code != 200:
        print(response2.text)
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 10
    assert _nfc(data2["first_name"]) == _nfc(employee_check["first_name"])
    assert _nfc(data2["last_name"]) == _nfc(employee_check["last_name"])
    assert data2["employee_number"] == employee_check["employee_number"]
    assert _nfc(data2["role"]) == _nfc(employee_check["role"])
    assert data2["active"] == employee_check["active"]
    assert _nfc(data2["notes"]) == _nfc(employee_check["notes"])

    # Check if we still have 4 records
    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 4
