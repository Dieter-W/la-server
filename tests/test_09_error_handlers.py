"""Global Flask error handlers (see app/errors.py)."""

from sqlalchemy.exc import SQLAlchemyError


def test_sqlalchemy_error_returns_database_error(app, client):
    """Uncaught SQLAlchemyError is mapped to 500 DATABASE_ERROR."""

    @app.route("/__test__/sqlalchemy_error", methods=["GET"])
    def raise_sqlalchemy_error():
        raise SQLAlchemyError("test failure")

    response = client.get("/__test__/sqlalchemy_error")
    assert response.status_code == 500
    data = response.get_json()

    assert data["error"] == "DATABASE_ERROR"
    assert "test failure" in data["message"]


def test_unhandled_exception_returns_internal_server_error(app, client):
    """Uncaught non-SQLAlchemy exception is mapped to 500 INTERNAL_SERVER_ERROR."""

    @app.route("/__test__/runtime_error", methods=["GET"])
    def raise_runtime_error():
        raise RuntimeError("unexpected")

    response = client.get("/__test__/runtime_error")
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected" in data["message"]
