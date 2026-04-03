"""Database tests"""


def test_endpoints(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_db_connectivity(client):
    response = client.get("/api/health/db")
    assert response.status_code == 200
