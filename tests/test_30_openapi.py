"""OpenAPI document and Swagger UI routes."""


def test_openapi_json(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    data = response.get_json()
    assert data["openapi"] == "3.0.3"
    assert "LA-Server" in data["info"]["title"]
    assert "/api/health" in data["paths"]
    assert "/api/auth/login" in data["paths"]
    assert data["components"]["securitySchemes"]["bearerAuth"]["type"] == "http"


def test_swagger_ui_docs(client):
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert b"swagger-ui" in response.data.lower()
    assert b"/api/openapi.json" in response.data
