"""Tests for ``/api/openapi.json`` and Swagger UI (``/api/docs``)."""


# ---------------------------------------------------------------------
# OpenAPI JSON
# ---------------------------------------------------------------------
def test_openapi_ok(client):
    """GET openapi.json returns 200, OpenAPI 3.0.3, paths and bearer scheme."""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    data = response.get_json()
    assert data["openapi"] == "3.0.3"
    assert "LA-Server" in data["info"]["title"]
    assert "/api/health" in data["paths"]
    assert "/api/auth/login" in data["paths"]
    assert data["components"]["securitySchemes"]["bearerAuth"]["type"] == "http"


# ---------------------------------------------------------------------
# Swagger UI HTML
# ---------------------------------------------------------------------
def test_swagger_ok(client):
    """GET /api/docs serves HTML that loads Swagger UI and references the spec URL."""
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert b"swagger-ui" in response.data.lower()
    assert b"/api/openapi.json" in response.data
