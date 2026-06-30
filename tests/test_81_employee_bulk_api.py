"""Bulk insert/update employees and validate them with an API call"""

import sys
import subprocess

from pathlib import Path
from urllib.parse import quote

from tests.test_utils import _login_as_admin, nfc

_REPO_ROOT = Path(__file__).resolve().parents[1]

employee_check = {
    "first_name": "Peter",
    "last_name": "Krause",
    "employee_number": "P00370",
    "role": "Leiter",
    "age": 40,
    "can_leave_alone": True,
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


# ---------------------------------------------------------------------
# Employees bulk import with API check
# ---------------------------------------------------------------------
def test_bulk_import_employees_create_ok(client,): # fmt: skip
    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "./data/csv-example/employees_sample.csv",
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
    assert nfc(peter["first_name"]) == nfc(employee_check["first_name"])
    assert nfc(peter["last_name"]) == nfc(employee_check["last_name"])
    assert peter["age"] == employee_check["age"]
    assert peter["can_leave_alone"] is employee_check["can_leave_alone"]
    assert nfc(peter["role"]) == nfc(employee_check["role"])
    assert peter["active"] is employee_check["active"]
    assert peter["notes"] == employee_check["notes"]


# ---------------------------------------------------------------------
# Employees bulk update with API check
# ---------------------------------------------------------------------
def test_bulk_import_employees_update_ok(client,): # fmt: skip

    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "./data/csv-example/employees_sample.csv",
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
    assert len(data) == 16
    assert nfc(data["first_name"]) == nfc(payload_put["first_name"])
    assert nfc(data["last_name"]) == nfc(payload_put["last_name"])
    assert nfc(data["role"]) == nfc(payload_put["role"])
    assert data["active"] is payload_put["active"]
    assert nfc(data["notes"]) == nfc(payload_put["notes"])
    assert data["full_time"] is True
    assert data["workday"] == "today"
    assert data["shift"] == "all-day"

    # In place update, with original data
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "./data/csv-example/employees_sample.csv",
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
    assert len(data2) == 16
    assert nfc(data2["first_name"]) == nfc(employee_check["first_name"])
    assert nfc(data2["last_name"]) == nfc(employee_check["last_name"])
    assert data2["employee_number"] == employee_check["employee_number"]
    assert data2["age"] == employee_check["age"]
    assert data2["can_leave_alone"] is employee_check["can_leave_alone"]
    assert nfc(data2["role"]) == nfc(employee_check["role"])
    assert data2["active"] == employee_check["active"]
    assert nfc(data2["notes"]) == nfc(employee_check["notes"])
    assert data2["full_time"] is True
    assert data2["workday"] == "today"
    assert data2["shift"] == "all-day"

    # Check if we still have 4 records
    response = client.get("/api/employees")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 4
