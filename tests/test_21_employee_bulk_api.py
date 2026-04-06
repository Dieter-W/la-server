"""Bulk insert/update employees and validate them with an API call"""

import sys
import subprocess

import unicodedata
from urllib.parse import quote

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


def test_bulk_import_employees_create(
    client,
):
    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Query all
    response = client.get("/api/employees")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert isinstance(data["employees"], list)
    assert len(data["employees"]) == 3
    assert data["count"] == 3

    assert any(
        _nfc(employee_data["first_name"]) == _nfc(employee_check["first_name"])
        for employee_data in data["employees"]
    )
    assert any(
        _nfc(employee_data["last_name"]) == _nfc(employee_check["last_name"])
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["employee_number"] == employee_check["employee_number"]
        for employee_data in data["employees"]
    )
    assert any(
        _nfc(employee_data["role"]) == _nfc(employee_check["role"])
        for employee_data in data["employees"]
    )
    assert any(
        employee_data["active"] == employee_check["active"]
        for employee_data in data["employees"]
    )
    assert any(
        _nfc(employee_data["notes"]) == _nfc(employee_check["notes"])
        for employee_data in data["employees"]
    )


def test_bulk_import_employees_update(
    client,
):
    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_employees.py",
            "employees_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Update the bulk input ...
    employee_number = employee_check["employee_number"]
    response = client.put(
        f"/api/employees/{quote(employee_number, safe='')}",
        json=payload_put,
    )

    # and check if update was successful
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 9
    assert _nfc(data["first_name"]) == _nfc(payload_put["first_name"])
    assert _nfc(data["last_name"]) == _nfc(payload_put["last_name"])
    assert _nfc(data["role"]) == _nfc(payload_put["role"])
    assert data["active"] == payload_put["active"]
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
    )

    # Check if the original content again available
    employee_number = employee_check["employee_number"]
    response2 = client.get(f"/api/employees/{quote(employee_number, safe='')}")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 9
    assert _nfc(data2["first_name"]) == _nfc(employee_check["first_name"])
    assert _nfc(data2["last_name"]) == _nfc(employee_check["last_name"])
    assert data2["employee_number"] == employee_check["employee_number"]
    assert _nfc(data2["role"]) == _nfc(employee_check["role"])
    assert data2["active"] == employee_check["active"]
    assert _nfc(data2["notes"]) == _nfc(employee_check["notes"])

    # Check if we have still 3 records
    response = client.get("/api/employees")
    assert response.status_code == 200
    data = response.get_json()
    print(data)
    assert data["count"] == 3
