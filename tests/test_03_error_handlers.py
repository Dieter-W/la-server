"""Global Flask error handlers (see app/errors.py)."""

from sqlalchemy.exc import OperationalError, SQLAlchemyError


def test_operational_error_concurrent_update(app, client):
    """MariaDB errno 1020 is mapped to 409 CONCURRENT_UPDATE."""

    @app.route("/__test__/concurrent_update", methods=["GET"])
    def raise_concurrent_update():
        raise OperationalError(
            "DELETE FROM job_assignments",
            {},
            Exception(
                1020, "Record has changed since last read in table 'job_assignments'"
            ),
        )

    response = client.get("/__test__/concurrent_update")
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "CONCURRENT_UPDATE"


def test_sqlalchemy_error_database(app, client):
    """Uncaught SQLAlchemyError is mapped to 500 DATABASE_ERROR without leaking details."""

    @app.route("/__test__/sqlalchemy_error", methods=["GET"])
    def raise_sqlalchemy_error():
        raise SQLAlchemyError("test failure")

    response = client.get("/__test__/sqlalchemy_error")
    assert response.status_code == 500
    data = response.get_json()

    assert data["error"] == "DATABASE_ERROR"
    # Exception details must not be exposed when DEBUG is False (production default).
    assert "message" not in data


def test_sqlalchemy_error_message_in_debug_mode(app, client):
    """In DEBUG mode, exception details are included to aid development."""
    app.config["DEBUG"] = True

    @app.route("/__test__/sqlalchemy_error_debug", methods=["GET"])
    def raise_sqlalchemy_error_debug():
        raise SQLAlchemyError("test failure debug")

    response = client.get("/__test__/sqlalchemy_error_debug")
    assert response.status_code == 500
    data = response.get_json()

    assert data["error"] == "DATABASE_ERROR"
    assert "test failure debug" in data["message"]

    app.config["DEBUG"] = False  # restore


def test_unhandled_exception_internal_server_error(app, client):
    """Uncaught non-SQLAlchemy exception is mapped to 500 INTERNAL_SERVER_ERROR without leaking details."""

    @app.route("/__test__/runtime_error", methods=["GET"])
    def raise_runtime_error():
        raise RuntimeError("unexpected")

    response = client.get("/__test__/runtime_error")
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "INTERNAL_SERVER_ERROR"
    # Exception details must not be exposed when DEBUG is False (production default).
    assert "message" not in data
