"""Company jobs max projection and effective cap tests."""

from urllib.parse import quote

from app.models import CompanyJobsMax
from app.schemas.company_jobs_max import resolve_company_jobs_max_slot
from app.schemas.part_time import ALL_WEEK_WORKDAY, WEEKDAYS_WORKDAY
from tests.test_part_time_helpers import assert_no_aggregate_workday_in_payload
from tests.test_utils import _login_as_employee, nfc


def _bank_from_list(data):
    return next(
        row for row in data["companies"] if nfc(row["company_name"]) == nfc("Bank")
    )


# ---------------------------------------------------------------------
# resolve_company_jobs_max_slot — unit precedence
# ---------------------------------------------------------------------
def test_resolve_company_jobs_max_slot_precedence():
    """Calendar-day row overrides ``weekdays`` for the same shift."""
    rows = [
        CompanyJobsMax(
            company_id=1, workday=WEEKDAYS_WORKDAY, shift="morning", jobs_max=2
        ),
        CompanyJobsMax(company_id=1, workday="wednesday", shift="morning", jobs_max=5),
    ]
    assert resolve_company_jobs_max_slot(rows, "wednesday", "morning").jobs_max == 5
    assert resolve_company_jobs_max_slot(rows, "tuesday", "morning").jobs_max == 2


def test_resolve_company_jobs_max_slot_precedence_calendar_over_weekdays_over_all_week():
    """Workday precedence: calendar day > ``weekdays`` > ``all-week``."""
    rows = [
        CompanyJobsMax(
            company_id=1, workday=ALL_WEEK_WORKDAY, shift="morning", jobs_max=1
        ),
        CompanyJobsMax(
            company_id=1, workday=WEEKDAYS_WORKDAY, shift="morning", jobs_max=2
        ),
        CompanyJobsMax(company_id=1, workday="tuesday", shift="morning", jobs_max=3),
    ]
    assert resolve_company_jobs_max_slot(rows, "tuesday", "morning").jobs_max == 3
    assert resolve_company_jobs_max_slot(rows, "wednesday", "morning").jobs_max == 2
    assert resolve_company_jobs_max_slot(rows, "saturday", "morning").jobs_max == 1


def test_resolve_company_jobs_max_slot_all_day_does_not_match_shift_lookup():
    """``all-day`` rows never match ``morning``/``afternoon`` shift lookups."""
    rows = [
        CompanyJobsMax(company_id=1, workday="wednesday", shift="all-day", jobs_max=3),
    ]
    assert resolve_company_jobs_max_slot(rows, "wednesday", "morning") is None
    assert resolve_company_jobs_max_slot(rows, "wednesday", "afternoon") is None
    assert resolve_company_jobs_max_slot(rows, "wednesday", "all-day").jobs_max == 3


# ---------------------------------------------------------------------
# GET /api/companies — list projection
# ---------------------------------------------------------------------
def test_companies_list_default_jobs_max_without_schedule(
    client, sample_company, sample_job_assignment
):
    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    bank = _bank_from_list(response.get_json())
    assert bank["default_jobs_max"] is True
    assert bank["workday"] == "today"
    assert bank["shift"] == "all-day"
    assert bank["jobs"]["max"] == 5


def test_companies_list_projects_schedule_on_wednesday_morning(
    client,
    sample_company,
    sample_job_assignment,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_weekdays,
):
    response = client.get("/api/companies")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    bank = _bank_from_list(response.get_json())
    assert bank["default_jobs_max"] is False
    assert bank["workday"] == "today"
    assert bank["shift"] == "morning"
    assert bank["jobs"]["max"] == 2
    assert bank["jobs"]["available"] == 1
    assert_no_aggregate_workday_in_payload(bank)


# ---------------------------------------------------------------------
# GET /api/companies/{name} — effective cap projection
# ---------------------------------------------------------------------
def test_companies_get_effective_cap_weekday_morning(
    client,
    sample_company,
    sample_job_assignment,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_weekdays,
):
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["default_jobs_max"] is False
    assert data["workday"] == "today"
    assert data["shift"] == "morning"
    assert data["jobs"]["max"] == 2
    assert data["jobs"]["available"] == 1


def test_companies_get_effective_cap_weekday_afternoon(
    client,
    sample_company,
    camp_is_wednesday,
    camp_shift_afternoon,
    company_jobs_max_bank_weekdays,
):
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["shift"] == "afternoon"
    assert data["jobs"]["max"] == 1
    assert data["jobs"]["available"] == 1


def test_companies_get_no_matching_slot_falls_back_to_default(
    client,
    sample_company,
    camp_is_saturday,
    camp_shift_morning,
    company_jobs_max_bank_weekdays,
):
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["default_jobs_max"] is False
    assert data["workday"] is None
    assert data["shift"] is None
    assert data["jobs"]["max"] == 5


def test_companies_get_calendar_override_precedence(
    client,
    sample_company,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_wednesday_override,
):
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["jobs"]["max"] == 5


def test_companies_get_all_week_morning_on_saturday(
    client,
    sample_company,
    camp_is_saturday,
    camp_shift_morning,
    company_jobs_max_bank_all_week_morning,
):
    """``all-week`` applies on weekends when no calendar or ``weekdays`` row matches."""
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["default_jobs_max"] is False
    assert data["workday"] == "today"
    assert data["shift"] == "morning"
    assert data["jobs"]["max"] == 4


def test_companies_get_allday_row_does_not_match_morning_shift(
    client,
    sample_company,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_wednesday_allday,
):
    """``all-day`` schedule row does not apply when ``camp_shift()`` is ``morning``."""
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["default_jobs_max"] is False
    assert data["workday"] is None
    assert data["shift"] is None
    assert data["jobs"]["max"] == 5


def test_companies_get_negative_jobs_available_when_cap_below_assignments(
    client,
    sample_company,
    sample_job_assignment,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_morning_zero,
):
    """``jobs.available`` may be negative when the effective cap is below assigned count."""
    response = client.get(f"/api/companies/{quote('Bank', safe='')}")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["jobs"]["max"] == 0
    assert data["jobs"]["available"] == -1


# ---------------------------------------------------------------------
# POST /api/job-assignments — effective cap enforcement
# ---------------------------------------------------------------------
def test_job_assignment_no_job_left_uses_effective_cap(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    sample_job_assignment,
    bank_active,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_morning_only,
):
    """Bank already has one assignment; morning schedule cap is 1 → NO_JOB_LEFT."""
    token = _login_as_employee(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "Bank",
            "employee_number": "A00265",
            "notes": "Should fail",
        },
    )
    if response.status_code != 400:
        print(response.text)
    assert response.status_code == 400
    assert response.get_json()["error"] == "NO_JOB_LEFT"


def test_job_assignment_allows_when_effective_cap_has_room(
    client,
    sample_authentication,
    sample_company,
    sample_employee,
    bank_active,
    camp_is_wednesday,
    camp_shift_morning,
    company_jobs_max_bank_weekdays,
):
    token = _login_as_employee(client, sample_authentication, sample_employee)
    response = client.post(
        "/api/job-assignments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "Bank",
            "employee_number": "A00265",
            "notes": "Second slot on morning cap 2",
        },
    )
    if response.status_code != 201:
        print(response.text)
    assert response.status_code == 201
