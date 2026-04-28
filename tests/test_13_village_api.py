"""Tests for village config and logo endpoints."""

from unittest.mock import patch

from app.routes import village_data as village_data_module


# ---------------------------------------------------------------------
# Village data JSON API
# ---------------------------------------------------------------------
def test_village_data_get_json_shape(client):
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


def test_village_data_not_modified_304(client):
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
# Village logo API
# ---------------------------------------------------------------------
def test_village_logo_served(client):
    response = client.get("/api/village-data/logo")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.data
    assert response.mimetype in ("image/jpeg", "image/jpg", "image/png", "image/webp")


def test_village_logo_not_configured(client):
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
