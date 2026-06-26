"""Context-aware workday/shift: fixed camp timezone and calendar-day cases."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import app.village_config as village_config_module
from app.errors import APIError
from app.schemas.part_time import (
    ALL_WEEK_WORKDAY,
    PART_TIME_CALENDAR_WORKDAYS,
    WEEKDAYS_CALENDAR_WORKDAYS,
    WEEKDAYS_WORKDAY,
    camp_day,
    is_weekdays_calendar_day,
    parse_list_workday_param,
    project_api_workday_label,
    resolve_part_time_slot,
    validate_part_time_combination,
)
from app.village_config import get_camp_timezone
from tests.test_camp_time import BERLIN, CAMP_MONDAY
from tests.test_part_time_helpers import (
    assert_no_aggregate_workday_in_payload,
    count_employees_matching_workday_filter,
    part_time_row,
    seed_part_time_rows,
)
from tests.test_utils import assert_status

# Camp timezone anchors: ``tests.test_camp_time`` (shared with conftest).


# ---------------------------------------------------------------------
# Schema helpers — fixed now + camp timezone
# ---------------------------------------------------------------------
def test_camp_day_monday_in_berlin():
    assert camp_day(now=CAMP_MONDAY, tz=BERLIN) == "monday"


def test_camp_day_naive_now_uses_camp_tz():
    naive = datetime(2026, 5, 18, 10, 0)
    assert camp_day(now=naive, tz=BERLIN) == "monday"


def test_camp_day_utc_instant_resolves_in_camp_tz():
    # 2026-05-17 22:00 UTC = 2026-05-18 00:00 CEST (Monday) in Berlin
    utc_sunday_night = datetime(2026, 5, 17, 22, 0, tzinfo=timezone.utc)
    assert camp_day(now=utc_sunday_night, tz=BERLIN) == "monday"


def test_parse_list_workday_param_all_on_monday():
    ctx = parse_list_workday_param("all", now=CAMP_MONDAY)
    assert ctx.filter_workday is None
    assert ctx.lookup_workday == "monday"
    assert ctx.response_label == "today"


def test_parse_list_workday_param_today_on_monday():
    ctx = parse_list_workday_param("today", now=CAMP_MONDAY)
    assert ctx.filter_workday == "monday"
    assert ctx.lookup_workday == "monday"
    assert ctx.response_label == "today"


def test_parse_list_workday_param_tuesday_on_monday():
    ctx = parse_list_workday_param("tuesday", now=CAMP_MONDAY)
    assert ctx.filter_workday == "tuesday"
    assert ctx.lookup_workday == "tuesday"
    assert ctx.response_label == "tuesday"


def test_get_camp_timezone_reads_ini():
    fake_ini = {"general": {"timezone": "America/Chicago"}}
    with patch.object(
        village_config_module, "load_village_data", return_value=fake_ini
    ):
        assert str(get_camp_timezone()) == "America/Chicago"


def test_get_camp_timezone_missing_falls_back_to_berlin():
    fake_ini = {"general": {"name": "Test Camp"}}
    with patch.object(
        village_config_module, "load_village_data", return_value=fake_ini
    ):
        assert str(get_camp_timezone()) == "Europe/Berlin"


def test_get_camp_timezone_invalid_falls_back_to_berlin():
    fake_ini = {"general": {"timezone": "Not/A/Timezone"}}
    with patch.object(
        village_config_module, "load_village_data", return_value=fake_ini
    ):
        assert str(get_camp_timezone()) == "Europe/Berlin"


# ---------------------------------------------------------------------
# GET /api/employees — list filters and response labels
# ---------------------------------------------------------------------
def test_employees_list_workday_all_labels_today_on_monday(
    client,
    camp_is_monday,
    part_time_monika,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees"), 200)
    assert data["count"] == 4

    by_number = {e["employee_number"]: e for e in data["employees"]}
    monika = by_number["M00252"]
    assert monika["workday"] == "today"
    assert monika["shift"] == "morning"
    assert monika["full_time"] is False

    assert by_number["P00370"]["workday"] == "today"
    assert by_number["P00370"]["shift"] == "all-day"
    assert by_number["P00370"]["full_time"] is True


def test_employees_list_workday_tuesday_filter_and_label(
    client,
    camp_is_monday,
    part_time_monika,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees?workday=tuesday"), 200)
    assert data["count"] == 1
    assert len(data["employees"]) == 1
    row = data["employees"][0]
    assert row["employee_number"] == "M00252"
    assert row["workday"] == "tuesday"
    assert row["shift"] == "afternoon"


def test_employees_list_workday_tuesday_shift_filter(
    client,
    camp_is_monday,
    part_time_monika,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(
        client.get("/api/employees?workday=tuesday&shift=afternoon"),
        200,
    )
    assert data["count"] == 1
    assert data["employees"][0]["shift"] == "afternoon"

    assert (
        assert_status(
            client.get("/api/employees?workday=tuesday&shift=morning"),
            200,
        )["count"]
        == 0
    )


def test_employees_list_workday_today_filters_monday_slot(
    client,
    camp_is_monday,
    part_time_monika,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees?workday=today"), 200)
    assert data["count"] == 1
    row = data["employees"][0]
    assert row["employee_number"] == "M00252"
    assert row["workday"] == "today"
    assert row["shift"] == "morning"


def test_employees_list_invalid_workday(client, sample_employee):
    assert (
        assert_status(client.get("/api/employees?workday=notaday"), 400)["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )


def test_employees_list_invalid_shift(client, sample_employee):
    assert (
        assert_status(
            client.get("/api/employees?workday=tuesday&shift=evening"),
            400,
        )["error"]
        == "INVALID_PART_TIME_SHIFT"
    )


def test_employees_list_shift_all_day_filter_and_response(
    client,
    camp_is_monday,
    part_time_anna_all_day,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    """Default part-time shift is all-day; filter and JSON use the same slug."""
    data = assert_status(
        client.get("/api/employees?workday=today&shift=all-day"),
        200,
    )
    assert data["count"] == 1
    row = data["employees"][0]
    assert row["employee_number"] == "A00265"
    assert row["workday"] == "today"
    assert row["shift"] == "all-day"
    assert row["full_time"] is False

    assert (
        assert_status(
            client.get("/api/employees?workday=today&shift=morning"),
            200,
        )["count"]
        == 0
    )

    assert assert_status(client.get("/api/employees/A00265"), 200)["shift"] == "all-day"


# ---------------------------------------------------------------------
# GET one / auth/me — calendar today in camp TZ
# ---------------------------------------------------------------------
def test_employees_get_one_workday_today_on_monday(
    client,
    camp_is_monday,
    part_time_monika,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees/M00252"), 200)
    assert data["workday"] == "today"
    assert data["shift"] == "morning"


def test_employees_get_one_full_time_projects_today_all_day(
    client,
    camp_is_monday,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees/P00370"), 200)
    assert data["workday"] == "today"
    assert data["shift"] == "all-day"
    assert data["full_time"] is True


def test_auth_me_workday_today_on_monday(
    client,
    camp_is_monday,
    part_time_monika,
    employee_headers,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(
        client.get("/api/auth/me", headers=employee_headers),
        200,
    )
    assert data["employee_number"] == "M00252"
    assert data["workday"] == "today"
    assert data["shift"] == "morning"


def test_auth_me_full_time_projects_today_all_day(
    client,
    camp_is_monday,
    admin_headers,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(
        client.get("/api/auth/me", headers=admin_headers),
        200,
    )
    assert data["employee_number"] == "P00370"
    assert data["full_time"] is True
    assert data["workday"] == "today"
    assert data["shift"] == "all-day"


# ---------------------------------------------------------------------
# Aggregate workdays — unit helpers
# ---------------------------------------------------------------------
def test_camp_day_only_uses_calendar_workdays():
    assert len(PART_TIME_CALENDAR_WORKDAYS) == 7
    assert WEEKDAYS_WORKDAY not in PART_TIME_CALENDAR_WORKDAYS
    assert ALL_WEEK_WORKDAY not in PART_TIME_CALENDAR_WORKDAYS


def test_is_weekdays_calendar_day_boundaries():
    assert WEEKDAYS_CALENDAR_WORKDAYS == PART_TIME_CALENDAR_WORKDAYS[:5]
    assert is_weekdays_calendar_day("monday") is True
    assert is_weekdays_calendar_day("friday") is True
    assert is_weekdays_calendar_day("saturday") is False
    assert is_weekdays_calendar_day("sunday") is False


def test_validate_part_time_combination_rejects_aggregate_all_day():
    ok, err = validate_part_time_combination(WEEKDAYS_WORKDAY, "all-day")
    assert ok is False
    assert err == "INVALID_PART_TIME_COMBINATION"

    ok, err = validate_part_time_combination(ALL_WEEK_WORKDAY, "all-day")
    assert ok is False
    assert err == "INVALID_PART_TIME_COMBINATION"

    ok, err = validate_part_time_combination(WEEKDAYS_WORKDAY, "All-Day")
    assert ok is False
    assert err == "INVALID_PART_TIME_COMBINATION"


def test_validate_part_time_combination_allows_aggregate_shift():
    ok, err = validate_part_time_combination(WEEKDAYS_WORKDAY, "morning")
    assert ok is True
    assert err is None

    ok, err = validate_part_time_combination("tuesday", "all-day")
    assert ok is True
    assert err is None


def test_project_api_workday_label_never_exposes_aggregate_slugs():
    assert project_api_workday_label(WEEKDAYS_WORKDAY) is None
    assert project_api_workday_label(ALL_WEEK_WORKDAY) is None
    assert project_api_workday_label("Weekdays") is None
    assert project_api_workday_label("today") == "today"
    assert project_api_workday_label("wednesday") == "wednesday"
    assert project_api_workday_label(None) is None


@pytest.mark.parametrize(
    ("part_time_fixture", "camp_fixture", "list_workday_params"),
    [
        (
            "part_time_anna_weekdays_morning",
            "camp_is_wednesday",
            ["all", "today", "wednesday", "friday", "saturday"],
        ),
        (
            "part_time_anna_all_week_morning",
            "camp_is_saturday",
            ["all", "today", "saturday", "sunday", "monday"],
        ),
    ],
)
def test_employee_json_never_exposes_aggregate_workday_slugs(
    client,
    request,
    sample_company,
    sample_employee,
    sample_job_assignment,
    part_time_fixture,
    camp_fixture,
    list_workday_params,
):
    """Employee list, GET one, and auth/me never return stored aggregate workday slugs."""
    request.getfixturevalue(part_time_fixture)
    request.getfixturevalue(camp_fixture)

    for workday_param in list_workday_params:
        data = assert_status(
            client.get(f"/api/employees?workday={workday_param}"),
            200,
        )
        for row in data["employees"]:
            assert_no_aggregate_workday_in_payload(row)

    assert_no_aggregate_workday_in_payload(
        assert_status(client.get("/api/employees/A00265"), 200)
    )


def test_resolve_part_time_slot_precedence_calendar_over_weekdays_over_all_week():
    rows = [
        part_time_row(ALL_WEEK_WORKDAY, "morning"),
        part_time_row(WEEKDAYS_WORKDAY, "morning"),
        part_time_row("tuesday", "afternoon"),
    ]
    assert resolve_part_time_slot(rows, "tuesday").shift == "afternoon"
    assert resolve_part_time_slot(rows, "wednesday").shift == "morning"
    assert resolve_part_time_slot(rows, "saturday").shift == "morning"


def test_resolve_part_time_slot_weekdays_does_not_match_weekend():
    rows = [part_time_row(WEEKDAYS_WORKDAY, "morning")]
    assert resolve_part_time_slot(rows, "friday") is not None
    assert resolve_part_time_slot(rows, "saturday") is None
    assert resolve_part_time_slot(rows, "sunday") is None


def test_resolve_part_time_slot_all_week_fills_weekend():
    rows = [part_time_row(ALL_WEEK_WORKDAY, "afternoon")]
    assert resolve_part_time_slot(rows, "saturday").shift == "afternoon"
    assert resolve_part_time_slot(rows, "sunday").shift == "afternoon"


def test_parse_list_workday_param_rejects_aggregate_slugs():
    with pytest.raises(APIError) as exc_info:
        parse_list_workday_param(WEEKDAYS_WORKDAY, now=CAMP_MONDAY)
    assert exc_info.value.message == "INVALID_PART_TIME_WORKDAY"

    with pytest.raises(APIError) as exc_info:
        parse_list_workday_param(ALL_WEEK_WORKDAY, now=CAMP_MONDAY)
    assert exc_info.value.message == "INVALID_PART_TIME_WORKDAY"


# ---------------------------------------------------------------------
# Aggregate workdays — GET /api/employees
# ---------------------------------------------------------------------
def test_employees_list_weekdays_morning_wednesday_filter_and_label(
    client,
    camp_is_wednesday,
    part_time_anna_weekdays_morning,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees?workday=wednesday"), 200)
    assert data["count"] == 1
    row = data["employees"][0]
    assert row["employee_number"] == "A00265"
    assert row["workday"] == "wednesday"
    assert row["shift"] == "morning"
    assert row["full_time"] is False


def test_employees_list_weekdays_morning_excluded_on_saturday(
    client,
    camp_is_saturday,
    part_time_anna_weekdays_morning,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    """``weekdays`` does not match Saturday in list filter or response projection."""
    assert (
        assert_status(client.get("/api/employees?workday=saturday"), 200)["count"] == 0
    )

    by_number = {
        e["employee_number"]: e
        for e in assert_status(client.get("/api/employees"), 200)["employees"]
    }
    assert by_number["A00265"]["workday"] is None
    assert by_number["A00265"]["shift"] is None


def test_employees_list_all_week_morning_included_on_saturday(
    client,
    camp_is_saturday,
    part_time_anna_all_week_morning,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees?workday=saturday"), 200)
    assert data["count"] == 1
    row = data["employees"][0]
    assert row["employee_number"] == "A00265"
    assert row["workday"] == "saturday"
    assert row["shift"] == "morning"


def test_employees_list_weekdays_plus_friday_afternoon_precedence(
    client,
    camp_is_friday,
    part_time_anna_weekdays_and_friday_afternoon,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    data = assert_status(client.get("/api/employees?workday=friday"), 200)
    assert data["count"] == 1
    row = data["employees"][0]
    assert row["employee_number"] == "A00265"
    assert row["workday"] == "friday"
    assert row["shift"] == "afternoon"

    assert (
        assert_status(
            client.get("/api/employees?workday=friday&shift=morning"),
            200,
        )["count"]
        == 0
    )

    thursday = assert_status(client.get("/api/employees?workday=thursday"), 200)[
        "employees"
    ][0]
    assert thursday["shift"] == "morning"


def test_employees_list_weekdays_included_on_friday(
    client,
    camp_is_friday,
    part_time_anna_weekdays_morning,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    """``weekdays`` matches Friday in list filter and projects ``today`` on ``workday=all``."""
    data = assert_status(client.get("/api/employees?workday=friday"), 200)
    assert data["count"] == 1
    row = data["employees"][0]
    assert row["employee_number"] == "A00265"
    assert row["workday"] == "friday"
    assert row["shift"] == "morning"

    by_number = {
        e["employee_number"]: e
        for e in assert_status(client.get("/api/employees"), 200)["employees"]
    }
    assert by_number["A00265"]["workday"] == "today"
    assert by_number["A00265"]["shift"] == "morning"


def test_employees_list_weekdays_morning_excluded_on_sunday(
    client,
    camp_is_sunday,
    part_time_anna_weekdays_morning,
    sample_company,
    sample_employee,
    sample_job_assignment,
):
    """``weekdays`` does not match Sunday in list filter or response projection."""
    assert assert_status(client.get("/api/employees?workday=sunday"), 200)["count"] == 0

    by_number = {
        e["employee_number"]: e
        for e in assert_status(client.get("/api/employees"), 200)["employees"]
    }
    assert by_number["A00265"]["workday"] is None
    assert by_number["A00265"]["shift"] is None


def test_employees_list_invalid_aggregate_workday_params(client, sample_employee):
    assert (
        assert_status(
            client.get(f"/api/employees?workday={WEEKDAYS_WORKDAY}"),
            400,
        )["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )

    assert (
        assert_status(
            client.get(f"/api/employees?workday={ALL_WEEK_WORKDAY}"),
            400,
        )["error"]
        == "INVALID_PART_TIME_WORKDAY"
    )


# ---------------------------------------------------------------------
# Filter parity — list count vs resolve_part_time_slot helper
# ---------------------------------------------------------------------
# (employee_id, workday, shift) rows for filter-vs-helper parity checks.
PART_TIME_FILTER_PARITY_SCENARIOS: dict[str, list[tuple[int, str, str]]] = {
    "weekdays_only": [(3, WEEKDAYS_WORKDAY, "morning")],
    "all_week_only": [(3, ALL_WEEK_WORKDAY, "morning")],
    "calendar_override": [
        (3, WEEKDAYS_WORKDAY, "morning"),
        (3, "friday", "afternoon"),
    ],
    "combined_precedence": [
        (3, WEEKDAYS_WORKDAY, "morning"),
        (2, ALL_WEEK_WORKDAY, "afternoon"),
        (2, "tuesday", "morning"),
    ],
}


@pytest.mark.parametrize("filter_day", PART_TIME_CALENDAR_WORKDAYS)
@pytest.mark.parametrize("scenario", list(PART_TIME_FILTER_PARITY_SCENARIOS))
def test_list_filter_matches_resolve_helper(
    filter_day,
    scenario,
    client,
    sample_company,
    sample_employee,
    sample_job_assignment,
    app,
):
    """List ``count`` must mirror ``resolve_part_time_slot`` across precedence scenarios."""
    rows = PART_TIME_FILTER_PARITY_SCENARIOS[scenario]
    with app.app_context():
        session = app.SessionLocal()
        seed_part_time_rows(session, rows)
        expected = count_employees_matching_workday_filter(session, filter_day)
        session.close()

    api_count = assert_status(
        client.get(f"/api/employees?workday={filter_day}"),
        200,
    )["count"]

    assert (
        api_count == expected
    ), f"scenario={scenario} filter_day={filter_day}: API {api_count} != helper {expected}"
