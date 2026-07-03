"""Tests for village config and logo endpoints."""

from unittest.mock import patch

from app.auth.utils import AUTH_GROUPS
from app.schemas.part_time import PART_TIME_SHIFTS, PART_TIME_STORED_WORKDAYS
from app.routes import village_data as village_data_module


# ---------------------------------------------------------------------
# Village data - Get JSON API
# ---------------------------------------------------------------------
def test_village_data_get_ok(client):
    """GET /api/village-data returns 200 with general, currency, village-images, and ETag."""
    response = client.get("/api/village-data")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert "general" in data
    assert "currency" in data
    assert "village-images" in data
    assert data["general"].get("name")
    assert "logo" in data["village-images"]
    assert response.headers.get("ETag")


def test_village_data_get_ok_etag(client):
    """If-None-Match with current ETag returns 304 and an empty body."""
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
    """Response la-server block exposes auth groups, part-time enums, checksum flag, and JWT TTLs."""
    response = client.get("/api/village-data")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert "la-server" in data
    ls = data["la-server"]
    assert ls["auth_groups"] == AUTH_GROUPS
    assert ls["part_time_shifts"] == PART_TIME_SHIFTS
    assert ls["part_time_workdays"] == PART_TIME_STORED_WORKDAYS
    assert ls["company_jobs_max_shifts"] == PART_TIME_SHIFTS
    assert ls["company_jobs_max_workdays"] == PART_TIME_STORED_WORKDAYS
    assert "weekdays" in ls["part_time_workdays"]
    assert "all-week" in ls["part_time_workdays"]
    calendar_only = [
        d for d in ls["part_time_workdays"] if d not in {"weekdays", "all-week"}
    ]
    assert calendar_only == [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    assert isinstance(ls["validate_employee_number_checksum"], bool)
    if ls["validate_employee_number_checksum"]:
        assert ls["employee_number_checksum_algorithm"] == "ISO_7064_MOD_97_10"
    else:
        assert ls["employee_number_checksum_algorithm"] is None
    assert isinstance(ls["jwt_access_ttl_minutes"], int)
    assert isinstance(ls["jwt_refresh_ttl_minutes"], int)


def test_village_data_get_ok_server_config_changes(client, app):
    """Changing server config updates ETag; a stale If-None-Match returns fresh 200 JSON."""
    response1 = client.get("/api/village-data")
    if response1.status_code != 200:
        print(response1.text)
    assert response1.status_code == 200
    etag_before = response1.headers["ETag"]

    prev = app.config["VALIDATE_CHECK_SUM"]
    app.config["VALIDATE_CHECK_SUM"] = not prev

    response2 = client.get("/api/village-data")
    if response2.status_code != 200:
        print(response2.text)
    assert response2.status_code == 200
    etag_after = response2.headers["ETag"]
    assert etag_before != etag_after

    stale = client.get(
        "/api/village-data", headers={"If-None-Match": f'"{etag_before}"'}
    )
    if stale.status_code != 200:
        print(stale.text)
    assert stale.status_code == 200
    assert stale.get_json() is not None


def test_village_data_get_ok_ini_file_changes(client):
    """la-server fields are injected by the server, not copied from INI la-server keys."""
    fake_ini = {
        "general": {"name": "X"},
        "la-server": {"should_not_appear": "ini-mistake"},
    }
    with patch.object(village_data_module, "load_village_data", return_value=fake_ini):
        response = client.get("/api/village-data")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert "should_not_appear" not in data["la-server"]
    assert data["la-server"]["auth_groups"] == AUTH_GROUPS
    assert data["la-server"]["part_time_shifts"] == PART_TIME_SHIFTS
    assert data["la-server"]["part_time_workdays"] == PART_TIME_STORED_WORKDAYS
    assert data["la-server"]["company_jobs_max_shifts"] == PART_TIME_SHIFTS
    assert data["la-server"]["company_jobs_max_workdays"] == PART_TIME_STORED_WORKDAYS


# ---------------------------------------------------------------------
# Village data - Get logo API
# ---------------------------------------------------------------------
def test_village_get_logo_ok(client):
    """GET /api/village-data/logo returns 200 image bytes and an ETag."""
    response = client.get("/api/village-data/logo")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.data
    assert response.mimetype in ("image/jpeg", "image/jpg", "image/png", "image/webp")
    assert response.headers.get("ETag")


def test_village_get_logo_ok_etag(client):
    """If-None-Match with current logo ETag returns 304 and an empty body."""
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
    """Missing logo configuration returns 404 VILLAGE_LOGO_NOT_CONFIGURED."""
    with patch.object(
        village_data_module,
        "load_village_data",
        return_value={"general": {}, "currency": {}, "village-images": {}},
    ):
        response = client.get("/api/village-data/logo")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "VILLAGE_LOGO_NOT_CONFIGURED"


# ---------------------------------------------------------------------
# Village data - Get favicon API
# ---------------------------------------------------------------------
def test_village_get_favicon_ok(client):
    """GET /api/village-data/favicon returns 200 image bytes and an ETag."""
    response = client.get("/api/village-data/favicon")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.data
    assert response.mimetype in ("image/png", "image/webp")
    assert response.headers.get("ETag")


def test_village_get_favicon_ok_etag(client):
    """If-None-Match with current favicon ETag returns 304 and an empty body."""
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
    """Missing favicon configuration returns 404 VILLAGE_FAVICON_NOT_CONFIGURED."""
    with patch.object(
        village_data_module,
        "load_village_data",
        return_value={
            "general": {},
            "currency": {},
            "village-images": {},
            "village-theme": {},
        },
    ):
        response = client.get("/api/village-data/favicon")
    if response.status_code != 404:
        print(response.text)
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "VILLAGE_FAVICON_NOT_CONFIGURED"
