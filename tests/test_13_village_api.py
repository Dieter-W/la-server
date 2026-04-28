"""Tests for village config and logo endpoints."""

from unittest.mock import patch

from app.routes import village_data as village_data_module


# ---------------------------------------------------------------------
# Village data - Get JSON API
# ---------------------------------------------------------------------
def test_village_data_get_ok(client):
    response = client.get("/api/village-data")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert "general" in data
    assert "currency" in data
    assert "images" in data
    assert data["general"].get("name")
    assert "logo" in data["images"]
    assert response.headers.get("ETag")


def test_village_data_get_ok_etag(client):
    response1 = client.get("/api/village-data")
    if response1.status_code != 200:
        print(response1.text)
    assert response1.status_code == 200
    etag = response1.headers["ETag"]
    response2 = client.get("/api/village-data", headers={"If-None-Match": f'"{etag}"'})
    if response2.status_code != 304:
        print(response2.text)
    assert response2.status_code == 304
    assert not response2.data


# ---------------------------------------------------------------------
# Village data - Get logo API
# ---------------------------------------------------------------------
def test_village_get_logo_ok(client):
    response = client.get("/api/village-data/logo")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.data
    assert response.mimetype in ("image/jpeg", "image/jpg", "image/png", "image/webp")
    assert response.headers.get("ETag")


def test_village_get_logo_ok_etag(client):
    response1 = client.get("/api/village-data/logo")
    if response1.status_code != 200:
        print(response1.text)
    assert response1.status_code == 200
    etag = response1.headers["ETag"]
    response2 = client.get(
        "/api/village-data/logo", headers={"If-None-Match": f'"{etag}"'}
    )
    if response2.status_code != 304:
        print(response2.text)
    assert response2.status_code == 304
    assert not response2.data


def test_village_get_logo_error_1(client):
    with patch.object(
        village_data_module,
        "_load_village_data",
        return_value={"general": {}, "currency": {}, "images": {}},
    ):
        response = client.get("/api/village-data/logo")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    assert response.get_json()["error"] == "VILLAGE_LOGO_NOT_CONFIGURED"


# ---------------------------------------------------------------------
# Village data - Get favicon API
# ---------------------------------------------------------------------
def test_village_get_favicon_ok(client):
    response = client.get("/api/village-data/favicon")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.data
    assert response.mimetype in ("image/png", "image/webp")
    assert response.headers.get("ETag")


def test_village_get_favicon_ok_etag(client):
    response1 = client.get("/api/village-data/favicon")
    if response1.status_code != 200:
        print(response1.text)
    assert response1.status_code == 200
    etag = response1.headers["ETag"]
    response2 = client.get(
        "/api/village-data/favicon", headers={"If-None-Match": f'"{etag}"'}
    )
    if response2.status_code != 304:
        print(response2.text)
    assert response2.status_code == 304
    assert not response2.data


def test_village_get_favicon_error_1(client):
    with patch.object(
        village_data_module,
        "_load_village_data",
        return_value={"general": {}, "currency": {}, "images": {}},
    ):
        response = client.get("/api/village-data/favicon")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    assert response.get_json()["error"] == "VILLAGE_FAVICON_NOT_CONFIGURED"
