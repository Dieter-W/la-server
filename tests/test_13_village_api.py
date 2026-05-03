"""Tests for village config and logo endpoints."""

from unittest.mock import patch

from app.auth.utils import AUTH_GROUPS
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


def test_village_data_get_ok_la_server(client):
    response = client.get("/api/village-data")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert "la-server" in data
    ls = data["la-server"]
    assert ls["auth_groups"] == AUTH_GROUPS
    assert isinstance(ls["validate_employee_number_checksum"], bool)
    if ls["validate_employee_number_checksum"]:
        assert ls["employee_number_checksum_algorithm"] == "ISO_7064_MOD_97_10"
    else:
        assert ls["employee_number_checksum_algorithm"] is None
    assert isinstance(ls["jwt_access_ttl_minutes"], int)
    assert isinstance(ls["jwt_refresh_ttl_minutes"], int)


def test_village_data_get_ok_server_config_changes(client, app):
    response1 = client.get("/api/village-data")
    assert response1.status_code == 200
    etag_before = response1.headers["ETag"]

    prev = app.config["VALIDATE_CHECK_SUM"]
    app.config["VALIDATE_CHECK_SUM"] = not prev

    response2 = client.get("/api/village-data")
    assert response2.status_code == 200
    etag_after = response2.headers["ETag"]
    assert etag_before != etag_after

    stale = client.get(
        "/api/village-data", headers={"If-None-Match": f'"{etag_before}"'}
    )
    assert stale.status_code == 200
    assert stale.get_json() is not None


def test_village_data_get_ok_ini_file_changes(client):
    fake_ini = {
        "general": {"name": "X"},
        "la-server": {"should_not_appear": "ini-mistake"},
    }
    with patch.object(village_data_module, "_load_village_data", return_value=fake_ini):
        response = client.get("/api/village-data")
    assert response.status_code == 200
    data = response.get_json()
    assert "should_not_appear" not in data["la-server"]
    assert data["la-server"]["auth_groups"] == AUTH_GROUPS


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
