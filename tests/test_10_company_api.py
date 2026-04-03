"""Company API tests"""

import unicodedata
from urllib.parse import quote

payload_create = {
    "company_name": "TEST_COMPANY",
    "number_of_jobs": 10,
    "pay_per_hour": 9,
    "active": True,
    "notes": "Created by create test",
}


payload_put = {
    "company_name": "Kitchen",
    "number_of_jobs": 5,
    "pay_per_hour": 99,
    "active": False,
    "notes": "Updated by test",
}


def _nfc(s: str) -> str:
    """Normalize Unicode so DB round-trips match Python string literals (NFC vs NFD)."""
    return unicodedata.normalize("NFC", s)


def test_query_all_companies(client, sample_company):
    # Get /api/companies
    response = client.get("/api/companies")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 4
    assert data["count"] == 4
    assert any(
        company_data["id"] == sample_company.id for company_data in data["companies"]
    )
    assert any(
        _nfc(company_data["company_name"]) == _nfc(sample_company.company_name)
        for company_data in data["companies"]
    )
    assert any(
        company_data["number_of_jobs"] == sample_company.number_of_jobs
        for company_data in data["companies"]
    )
    assert any(
        company_data["pay_per_hour"] == sample_company.pay_per_hour
        for company_data in data["companies"]
    )
    assert any(
        company_data["active"] == sample_company.active
        for company_data in data["companies"]
    )
    assert any(
        company_data["notes"] == sample_company.notes
        for company_data in data["companies"]
    )


def test_query_all_companies_true(
    client,
    sample_company,
):
    # Get /api/companies?active=true
    response = client.get("/api/companies?active=true")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 3
    assert data["count"] == 3


def test_query_all_companies_false(
    client,
    sample_company,
):
    # Get /api/companies?active=false
    response = client.get("/api/companies?active=false")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 1
    assert data["count"] == 1


def test_query_all_companies_empty(
    client,
    db_session,
):
    # Get /api/companies
    response = client.get("/api/companies")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 0
    assert data["companies"] == []
    assert data["count"] == 0


def test_query_company(
    client,
    sample_company,
):
    # Get /api/companies/<company_name>
    company_name = sample_company.company_name
    response = client.get(f"/api/companies/{quote(company_name, safe='')}")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert _nfc(data["company_name"]) == _nfc(company_name)


def test_create_company(
    client,
    sample_company,
):
    # Post /api/companies
    response = client.post("/api/companies", json=payload_create)
    assert response.status_code == 201
    data = response.get_json()
    assert isinstance(data, dict)


def test_create_company_duplicate(
    client,
    sample_company,
):
    # Post /api/companies
    response = client.post("/api/companies", json=payload_create)
    response = client.post("/api/companies", json=payload_create)
    assert response.status_code == 409


def test_update_company(client, sample_company):
    # Put /api/companies/<company_name>
    company_name = sample_company.company_name
    response = client.put(
        f"/api/companies/{quote(company_name, safe='')}",
        json=payload_put,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 8
    assert data["id"] == sample_company.id
    assert _nfc(data["company_name"]) == _nfc(payload_put["company_name"])
    assert data["number_of_jobs"] == payload_put["number_of_jobs"]
    assert data["pay_per_hour"] == payload_put["pay_per_hour"]
    assert data["active"] == payload_put["active"]
    assert data["notes"] == payload_put["notes"]

    response2 = client.get("/api/companies/Kitchen")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert isinstance(data2, dict)
    assert len(data2) == 8
    assert data2["company_name"] == payload_put["company_name"]


def test_delete_company(client, sample_company):
    # Delete /api/companies/<company_name>
    company_name = sample_company.company_name
    response = client.delete(f"/api/companies/{quote(company_name, safe='')}")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    response = client.get(f"/api/companies/{quote(company_name, safe='')}")
    assert response.status_code == 404
