"""Test Kinderspielstadt Los Ämmerles - LA-Server"""

import os
import sys
import pytest

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

from app import create_app
from app.database import db
from app.models import Employee, Company

from app.config import Config


# ---------------------------------------------------------
# 1. Create Test Database
# ---------------------------------------------------------
@pytest.fixture()
def env_patch(monkeypatch):
    """Set needed environment variables"""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("MARIADB_DATABASE", "$$test-database$$")

    yield


@pytest.fixture()
def db_create(env_patch):
    engine = create_engine(Config.admin_db_uri())
    with engine.connect() as conn:
        mariadb_db = os.getenv("MARIADB_DATABASE")
        conn.execute(text(f"DROP DATABASE IF EXISTS `{mariadb_db}`"))
        conn.execute(text(f"CREATE DATABASE `{mariadb_db}`"))

        yield

        with engine.connect() as conn:
            mariadb_db = os.getenv("MARIADB_DATABASE")
            conn.execute(text(f"DROP DATABASE IF EXISTS `{mariadb_db}`"))


# ---------------------------------------------------------
# 2. Flask test client fixture
# ---------------------------------------------------------
@pytest.fixture()
def app(db_create):
    """Create and configure a Flask app for testing"""

    app = create_app(Config)
    with app.app_context():
        db.create_all()

        yield app

        db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client fixture"""
    return app.test_client()


# ---------------------------------------------------------
# 3. Database session fixture
# ---------------------------------------------------------
@pytest.fixture()
def db_session(app):
    """
    Provide a clean database session for each test.
    Rollback after test to isolate tests.
    """
    connection = db.engine.connect()
    transaction = connection.begin()

    # Bind Flask session to this transaction
    # Keep fixture objects usable after commit() inside tests/fixtures.
    Session = scoped_session(sessionmaker(bind=connection, expire_on_commit=False))
    db.session = Session

    yield db.session

    transaction.rollback
    db.session.remove()
    connection.close()


# ---------------------------------------------------------
# 4. Sample data fixture
# ---------------------------------------------------------
@pytest.fixture()
def sample_company(
    app,
):
    """Add 4 companies for testing"""
    with app.app_context():
        session = app.SessionLocal()

        company = Company(
            company_name="Bank",
            number_of_jobs=10,
            pay_per_hour=9,
            active=True,
            notes="Created by test script",
        )
        session.add(company)
        company = Company(
            company_name="Arbeitsamt",
            number_of_jobs=10,
            pay_per_hour=9,
            active=True,
            notes="Created by test script",
        )
        session.add(company)
        company = Company(
            company_name="Bauhof",
            number_of_jobs=10,
            pay_per_hour=9,
            active=False,
            notes="Created by test script",
        )
        session.add(company)
        company = Company(
            company_name="Küche",
            number_of_jobs=10,
            pay_per_hour=9,
            active=True,
            notes="Created by test script",
        )
        session.add(company)
        session.commit()

        yield company

        session.close()

    return company


@pytest.fixture()
def sample_employee(
    app,
):
    """Add 4 employees for testing"""
    with app.app_context():
        session = app.SessionLocal()

        employee = Employee(
            first_name="Max",
            last_name="Mustermann",
            employee_number="M00155",
            role="Betreuer",
            active=False,
            notes="Created by test script",
        )
        session.add(employee)
        employee = Employee(
            first_name="Anna",
            last_name="Schmidt",
            employee_number="A00265",
            role="Helferin",
            active=True,
            notes="Created by test script",
        )
        session.add(employee)
        employee = Employee(
            first_name="Peter",
            last_name="Krause",
            employee_number="P00370",
            role="Leiter",
            active=True,
            notes="Created by test script",
        )
        session.add(employee)

        session.commit()

        yield employee

        session.close()

    return employee
