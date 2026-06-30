"""Test Kinderspielstadt Los Ämmerles - LA-Server"""

import os
import sys
import pytest

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool

from app import create_app
from app.database import db
from app.models import Authentication, Company, Employee, JobAssignment, PartTime
from app.auth.utils import hash_password

from app.config import Config
from app.camp_time import camp_day
from app.schemas.part_time import ALL_WEEK_WORKDAY, WEEKDAYS_WORKDAY
from tests.test_camp_time import (
    BERLIN,
    CAMP_FRIDAY,
    CAMP_MONDAY,
    CAMP_SATURDAY,
    CAMP_SUNDAY,
    CAMP_WEDNESDAY,
    camp_today_patch,
)
from tests.test_part_time_helpers import seed_part_time_rows


def _camp_day_patch(camp_instant: datetime):
    """Pin ``camp_day()`` to a fixed calendar day in camp timezone."""

    def _fixed(*, now=None, tz=None):
        return camp_day(now=camp_instant, tz=tz or BERLIN)

    return patch("app.camp_time.camp_day", side_effect=_fixed)


def _mariadb_test_database_name(worker_id: str) -> str:
    """Unique DB name per pytest-xdist worker; valid MariaDB identifier (<=64 chars)."""
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in worker_id)
    name = f"la_test_{safe}"
    return name[:64]


# ---------------------------------------------------------
# 1. Create Test Database
# ---------------------------------------------------------
@pytest.fixture()
def env_patch(monkeypatch, worker_id):
    """Set needed environment variables (isolated DB per xdist worker)."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("MARIADB_DATABASE", _mariadb_test_database_name(worker_id))

    yield


@pytest.fixture()
def db_create(env_patch):
    """Provision test DB via short-lived admin connections (not held across the test)."""
    mariadb_db = os.getenv("MARIADB_DATABASE")
    engine = create_engine(Config.admin_db_uri(), poolclass=NullPool)
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{mariadb_db}`"))
            conn.execute(text(f"CREATE DATABASE `{mariadb_db}`"))
        yield
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{mariadb_db}`"))
    finally:
        engine.dispose()


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
        db.engine.dispose()


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

    transaction.rollback()
    db.session.remove()
    connection.close()


# ---------------------------------------------------------
# 4. Sample data fixture
# ---------------------------------------------------------
@pytest.fixture()
def sample_authentication(
    app,
    sample_employee,
):
    """Add 4 authentication employees for testing"""
    with app.app_context():
        session = app.SessionLocal()

        authentication = Authentication(
            employee_id=1,  # M00155
            password_hash=hash_password("Mustermann"),
            password_must_change=False,
            auth_group="employee",
            notes="Created by test script",
        )
        session.add(authentication)

        authentication = Authentication(
            employee_id=2,  # M00252
            password_hash=hash_password("Mustermann"),
            password_must_change=True,
            auth_group="employee",
            notes="Created by test script",
        )
        session.add(authentication)

        authentication = Authentication(
            employee_id=3,  # A00265
            password_hash=hash_password("Schmidt"),
            password_must_change=False,
            auth_group="staff",
            notes="Created by test script",
        )
        session.add(authentication)

        authentication = Authentication(
            employee_id=4,  # P00370
            password_hash=hash_password("Krause"),
            password_must_change=True,
            auth_group="admin",
            notes="Created by test script",
        )
        session.add(authentication)

        session.commit()

        yield authentication

        session.close()


@pytest.fixture()
def sample_company(
    app,
):
    """Add 4 companies for testing"""
    with app.app_context():
        session = app.SessionLocal()

        company = Company(
            company_name="Bank",
            jobs_max=5,
            hourly_pay=9,
            active=False,
            notes="Created by test script",
        )
        session.add(company)
        company = Company(
            company_name="Arbeitsamt",
            jobs_max=10,
            hourly_pay=9,
            active=True,
            notes="Created by test script",
        )
        session.add(company)
        company = Company(
            company_name="Küche",
            jobs_max=2,
            hourly_pay=9,
            active=True,
            notes="Created by test script",
        )
        session.add(company)
        company = Company(
            company_name="Bauhof",
            jobs_max=1,
            hourly_pay=9,
            active=True,
            notes="Created by test script",
        )
        session.add(company)
        session.commit()

        yield company

        session.close()


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
            age=7,
            can_leave_alone=False,
            role="Betreuer",
            active=False,
            notes="Created by test script",
        )
        session.add(employee)

        employee = Employee(
            first_name="Monika",
            last_name="Mustermann",
            employee_number="M00252",
            age=12,
            can_leave_alone=True,
            role="Betreuer",
            active=True,
            notes="Created by test script",
        )
        session.add(employee)

        employee = Employee(
            first_name="Anna",
            last_name="Schmidt",
            employee_number="A00265",
            age=28,
            can_leave_alone=True,
            role="Helferin",
            active=True,
            notes="Created by test script",
        )
        session.add(employee)

        employee = Employee(
            first_name="Peter",
            last_name="Krause",
            employee_number="P00370",
            age=40,
            can_leave_alone=True,
            role="Leiter",
            active=True,
            notes="Created by test script",
        )
        session.add(employee)

        session.commit()

        yield employee

        session.close()


@pytest.fixture()
def sample_employee_part_time(
    app,
    sample_employee,
):
    """Add 2 part-time employees for testing"""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(
            session,
            [
                (3, "monday", "morning"),  # A00265
                (3, "tuesday", "afternoon"),
                (4, "wednesday", "all-day"),  # P00370
                (4, "thursday", "all-day"),
            ],
        )
        part_time_employee = (
            session.query(PartTime).order_by(PartTime.id.desc()).first()
        )
        yield part_time_employee
        session.close()


@pytest.fixture()
def sample_job_assignment(
    app,
    sample_employee,
    sample_company,
):
    """Add 2 job assignments for testing"""
    with app.app_context():
        session = app.SessionLocal()

        job_assignment = JobAssignment(
            company_id=1,  # Bank
            employee_id=1,  # M00155
            notes="Created by test script",
        )
        session.add(job_assignment)

        job_assignment = JobAssignment(
            company_id=4,  # Bauhof
            employee_id=4,  # P00370
            notes="Created by test script",
        )
        session.add(job_assignment)

        session.commit()

        yield job_assignment

        session.close()


# ---------------------------------------------------------
# 5. Shared time fixtures
# ---------------------------------------------------------
@pytest.fixture
def camp_is_monday():
    """Pin calendar today to Monday via fixed ``now`` in camp timezone."""
    with _camp_day_patch(CAMP_MONDAY):
        yield


@pytest.fixture
def camp_today_is_monday():
    """Pin ``camp_today()`` to Monday 2026-05-18 across all camp targets."""
    with camp_today_patch(CAMP_MONDAY):
        yield


@pytest.fixture
def camp_is_wednesday():
    """Pin calendar today to Wednesday via fixed ``now`` in camp timezone."""
    with _camp_day_patch(CAMP_WEDNESDAY):
        yield


@pytest.fixture
def camp_is_friday():
    """Pin calendar today to Friday via fixed ``now`` in camp timezone."""
    with _camp_day_patch(CAMP_FRIDAY):
        yield


@pytest.fixture
def camp_is_saturday():
    """Pin calendar today to Saturday via fixed ``now`` in camp timezone."""
    with _camp_day_patch(CAMP_SATURDAY):
        yield


@pytest.fixture
def camp_is_sunday():
    """Pin calendar today to Sunday via fixed ``now`` in camp timezone."""
    with _camp_day_patch(CAMP_SUNDAY):
        yield


# ---------------------------------------------------------
# 6. Part-time scenario fixtures (employee projection tests)
# ---------------------------------------------------------
@pytest.fixture
def part_time_monika(app, sample_employee):
    """Monika (id 2): Monday morning + Tuesday afternoon part-time slots."""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(
            session,
            [
                (2, "monday", "morning"),
                (2, "tuesday", "afternoon"),
            ],
        )
        session.close()


@pytest.fixture
def part_time_anna_all_day(app, sample_employee):
    """Anna (id 3): Monday slot with default full-day shift (all-day)."""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(session, [(3, "monday", "all-day")])
        session.close()


@pytest.fixture
def part_time_anna_weekdays_morning(app, sample_employee):
    """Anna (id 3): ``weekdays`` morning aggregate slot."""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(session, [(3, WEEKDAYS_WORKDAY, "morning")])
        session.close()


@pytest.fixture
def part_time_anna_all_week_morning(app, sample_employee):
    """Anna (id 3): ``all-week`` morning aggregate slot."""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(session, [(3, ALL_WEEK_WORKDAY, "morning")])
        session.close()


@pytest.fixture
def part_time_anna_weekdays_and_friday_afternoon(app, sample_employee):
    """Anna (id 3): ``weekdays`` morning + Friday afternoon override."""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(
            session,
            [
                (3, WEEKDAYS_WORKDAY, "morning"),
                (3, "friday", "afternoon"),
            ],
        )
        session.close()


@pytest.fixture
def part_time_monika_unsorted_rows(app, sample_employee):
    """Monika (id 2): rows in non-canonical order for list-sort tests."""
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(
            session,
            [
                (2, "friday", "morning"),
                (2, "monday", "afternoon"),
                (2, WEEKDAYS_WORKDAY, "morning"),
                (2, ALL_WEEK_WORKDAY, "afternoon"),
            ],
        )
        session.close()
