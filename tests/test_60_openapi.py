"""Tests for ``/api/openapi.json`` and Swagger UI (``/api/docs``)."""


# ---------------------------------------------------------------------
# OpenAPI JSON
# ---------------------------------------------------------------------
def test_openapi_ok(client):
    """GET openapi.json returns 200, OpenAPI 3.0.3, paths and bearer scheme."""
    response = client.get("/api/openapi.json")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    data = response.get_json()
    assert data["openapi"] == "3.0.3"
    assert "LA-Server" in data["info"]["title"]
    assert "/api/health" in data["paths"]
    assert "/api/auth/login" in data["paths"]
    assert "/api/part-time/{employee_number}" in data["paths"]
    assert data["components"]["securitySchemes"]["bearerAuth"]["type"] == "http"


def test_openapi_attendance_paths(client):
    """OpenAPI spec documents check-in, check-out, and attendance list/history endpoints."""
    response = client.get("/api/openapi.json")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    paths = data["paths"]
    schemas = data["components"]["schemas"]

    assert "/api/attendance/check-in/{employee_number}" in paths
    assert paths["/api/attendance/check-in/{employee_number}"]["post"]["tags"] == [
        "Attendance"
    ]

    assert "/api/attendance/check-out/{employee_number}" in paths
    assert paths["/api/attendance/check-out/{employee_number}"]["post"]["tags"] == [
        "Attendance"
    ]

    assert "/api/check-in/{employee_number}" not in paths
    assert "/api/check-out/{employee_number}" not in paths

    assert "/api/attendance/check-ins" in paths
    assert "get" in paths["/api/attendance/check-ins"]
    assert paths["/api/attendance/check-ins"]["get"]["tags"] == ["Attendance"]

    assert "/api/attendance/check-outs" in paths
    assert "get" in paths["/api/attendance/check-outs"]
    assert paths["/api/attendance/check-outs"]["get"]["tags"] == ["Attendance"]

    assert "/api/check-ins" not in paths
    assert "/api/check-outs" not in paths

    assert "/api/attendance/{employee_number}" in paths
    assert "get" in paths["/api/attendance/{employee_number}"]
    assert paths["/api/attendance/{employee_number}"]["get"]["tags"] == ["Attendance"]

    assert "AttendanceMutationResponse" in schemas
    assert "ListCheckInsResponse" in schemas
    assert "ListCheckOutsResponse" in schemas
    assert "ListAttendanceResponse" in schemas
    assert "checked_in" in schemas["EmployeeResponse"]["properties"]


# ---------------------------------------------------------------------
# Swagger UI HTML
# ---------------------------------------------------------------------
def test_swagger_ok(client):
    """GET /api/docs serves HTML that loads Swagger UI and references the spec URL."""
    response = client.get("/api/docs")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    assert b"swagger-ui" in response.data.lower()
    assert b"/api/openapi.json" in response.data
