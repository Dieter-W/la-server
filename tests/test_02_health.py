"""Endpoint and Database tests"""


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
