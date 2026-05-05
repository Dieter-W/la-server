"""Bulk insert/update companies and validate them with an API call"""

import sys
import subprocess

import unicodedata
from urllib.parse import quote

from test_utils import _login_as_admin

company_check = {
    "company_name": "Küche",
    "jobs": {
        "max": 10,
        "available": 10,
    },
    "hourly_pay": 15,
    "active": False,
    "notes": "Only weekdays",
}

payload_put = {
    "jobs_max": 5,
    "hourly_pay": 99,
    "active": True,
    "notes": "Updated by test",
}


def _nfc(s: str) -> str:
    """Normalize Unicode so DB round-trips match Python string literals (NFC vs NFD)."""
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------
# Companies bulk import with API check
# ---------------------------------------------------------------------
def test_bulk_import_companies_create(client,): # fmt: skip
    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_companies.py",
            "./data/csv-example/companies_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Query all
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
        _nfc(company_data["company_name"]) == _nfc(company_check["company_name"])
        for company_data in data["companies"]
    )
    assert any(
        company_data["jobs"]["max"] == company_check["jobs"]["max"]
        for company_data in data["companies"]
    )
    assert any(
        company_data["jobs"]["available"] == company_check["jobs"]["available"]
        for company_data in data["companies"]
    )
    assert any(
        company_data["hourly_pay"] == company_check["hourly_pay"]
        for company_data in data["companies"]
    )
    assert any(
        company_data["active"] == company_check["active"]
        for company_data in data["companies"]
    )
    assert any(
        company_data["notes"] == company_check["notes"]
        for company_data in data["companies"]
    )


# ---------------------------------------------------------------------
# Companies bulk update with API check
# ---------------------------------------------------------------------
def test_bulk_import_companies_update(client, sample_authentication, sample_employee,): # fmt: skip
    token = _login_as_admin(client, sample_authentication, sample_employee,) # fmt: skip
    # Bulk insert
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_companies.py",
            "./data/csv-example/companies_sample.csv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Update the bulk input ...
    company_name = company_check["company_name"]
    response = client.put(
        f"/api/companies/{quote(company_name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_put,
    )
    # and check if update was successful
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 8
    assert data["jobs"]["max"] == payload_put["jobs_max"]
    assert data["jobs"]["available"] == payload_put["jobs_max"]
    assert data["hourly_pay"] == payload_put["hourly_pay"]
    assert data["active"] == payload_put["active"]
    assert data["notes"] == payload_put["notes"]

    # In place update, with original data
    result = subprocess.run(
        [
            sys.executable,
            "./scripts/bulk_import_companies.py",
            "./data/csv-example/companies_sample.csv",
        ],
        capture_output=True,
        text=True,
    )

    # Check if the original content again available
    company_name = company_check["company_name"]
    response2 = client.get(f"/api/companies/{quote(company_name, safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 8
    assert _nfc(data2["company_name"]) == _nfc(company_check["company_name"])
    assert data["jobs"]["max"] == payload_put["jobs_max"]
    assert data["jobs"]["available"] == payload_put["jobs_max"]
    assert data2["hourly_pay"] == company_check["hourly_pay"]
    assert data2["active"] == company_check["active"]
    assert data2["notes"] == company_check["notes"]

    # Check if we have still 4 records
    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 4
