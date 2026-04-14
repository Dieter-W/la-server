"""Endpoint and Database tests"""

from unittest.mock import MagicMock, patch

from app.routes.health import database_summary


# ---------------------------------------------------------------------
# General endpoint check
# ---------------------------------------------------------------------
def test_endpoints(client):
    response = client.get("/api/health")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200


# ---------------------------------------------------------------------
# General database check
# ---------------------------------------------------------------------
def test_db_connectivity(client):
    response = client.get("/api/health/db")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200


def test_db_connectivity_error_1(client):
    """When SELECT 1 fails, health/db returns 503 and an error-shaped JSON body."""
    mock_session = MagicMock()
    mock_session.execute.side_effect = RuntimeError("connection refused")
    mock_g = MagicMock()
    mock_g.db = mock_session
    with patch("app.routes.health.g", mock_g):
        response = client.get("/api/health/db")
    if response.status_code != 503:
        print(response.text)
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert "connection refused" in data["database"]


# ---------------------------------------------------------------------
# Health runtime check
# ---------------------------------------------------------------------
def test_health_runtime_shape(client):
    response = client.get("/api/health/runtime")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "Kinderspielstadt Los Ämmerles - LA-Server"
    assert "python_version" in data["runtime"]
    assert "platform" in data["runtime"]
    assert "pid" in data["runtime"]
    assert data["runtime"]["uptime_seconds"] is not None
    assert isinstance(data["runtime"]["uptime_seconds"], (int, float))
    assert "DEBUG" in data["config"]
    assert "TESTING" in data["config"]
    assert "LOG_LEVEL" in data["config"]
    assert "url_redacted" in data["database"]
    assert "host" in data["database"]
    assert "database" in data["database"]
    assert data["pool"]["pool_type"] == "QueuePool"
    for key in ("size", "checked_in", "checked_out", "overflow", "status"):
        assert key in data["pool"]
    conc = data["concurrency"]
    for section in ("pool_connections", "requests_with_db_session"):
        assert section in conc
        assert conc[section]["active"] >= 0
        assert conc[section]["max_historic"] >= conc[section]["active"]
    assert conc["requests_with_db_session"]["max_historic"] >= 1


# ---------------------------------------------------------------------
# Database summary check
# ---------------------------------------------------------------------
def test_database_summary_redacts_password():
    secret = "LEAK_TEST_SECRET_12345"
    cfg = {
        "SQLALCHEMY_DATABASE_URI": (
            f"mysql+pymysql://u:{secret}@dbhost.example:3306/mydb"
        )
    }
    out = database_summary(cfg)
    assert secret not in out["url_redacted"]
    assert secret not in str(out)
