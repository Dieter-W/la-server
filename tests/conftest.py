"""Test Spielstadt server"""

import sys
import pytest

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

from app import create_app
from app.database import db
from app.models import Employee, Company

from app.config import TestingConfig


# ---------------------------------------------------------
# 1. Create Test Database
# ---------------------------------------------------------
@pytest.fixture()
def db_create():
    engine = create_engine(TestingConfig.ADMIN_DB_URI)
    with engine.connect() as conn:
        conn.execute(
            text(f"DROP DATABASE IF EXISTS `{TestingConfig.MARIADB_DATABASE}`")
        )
        conn.execute(text(f"CREATE DATABASE `{TestingConfig.MARIADB_DATABASE}`"))

        yield

        with engine.connect() as conn:
            conn.execute(
                text(f"DROP DATABASE IF EXISTS `{TestingConfig.MARIADB_DATABASE}`")
            )


# ---------------------------------------------------------
# 2. Flask test client fixture
# ---------------------------------------------------------
@pytest.fixture()
def app(db_create):
    """Create and configure a Flask app for testing"""
    app = create_app(TestingConfig)
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
    Session = scoped_session(sessionmaker(bind=connection))
    db.session = Session

    yield db.session

    transaction.rollback
    db.session.remove()
    connection.close()


# ---------------------------------------------------------
# 4. Sample data fixture
# ---------------------------------------------------------
@pytest.fixture()
def sample_company(db_session):
    """Add 4 companies for testing"""

    company = Company(
        company_name="Bank",
        number_of_jobs=10,
        pay_per_hour=9,
        active=True,
        notes="Created by test script",
    )
    db.session.add(company)
    company = Company(
        company_name="Arbeitsamt",
        number_of_jobs=10,
        pay_per_hour=9,
        active=True,
        notes="Created by test script",
    )
    db.session.add(company)
    company = Company(
        company_name="Bauhof",
        number_of_jobs=10,
        pay_per_hour=9,
        active=False,
        notes="Created by test script",
    )
    db.session.add(company)
    company = Company(
        company_name="Küche",
        number_of_jobs=10,
        pay_per_hour=9,
        active=True,
        notes="Created by test script",
    )
    db.session.add(company)

    db.session.commit()
    return company


@pytest.fixture()
def sample_employee(db_session):
    """Add 4 employees for testing"""
    employee = Employee(
        first_name="Max",
        last_name="Mustermann",
        employee_number="M00155",
        role="Betreuer",
        active=False,
        notes="Created by test script",
    )
    db.session.add(employee)
    employee = Employee(
        first_name="Anna",
        last_name="Schmidt",
        employee_number="A00265",
        role="Helferin",
        active=True,
        notes="Created by test script",
    )
    db.session.add(employee)
    employee = Employee(
        first_name="Peter",
        last_name="Krause",
        employee_number="P00370",
        role="Leiter",
        active=True,
        notes="Created by test script",
    )
    db.session.add(employee)

    db.session.commit()
    return employee
