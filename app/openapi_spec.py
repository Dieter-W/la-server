"""OpenAPI 3.0 schema for the LA-Server REST API. Narrative docs: docs/developer-guide.md."""

import tomllib
from pathlib import Path

from app.schemas.part_time import (
    PART_TIME_API_WORKDAY_LABELS,
    PART_TIME_CALENDAR_WORKDAYS,
    PART_TIME_STORED_WORKDAYS,
)

# ---------------------------------------------------------------------
# Project version
# ---------------------------------------------------------------------


def _read_project_version() -> str:
    """Read the canonical version from pyproject.toml."""
    toml_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------
# Static OpenAPI document fragments
# ---------------------------------------------------------------------

API_TITLE = "LA-Server API"
API_DESCRIPTION = (
    "Kinderspielstadt Los Ämmerles JSON REST API (companies, employees, part-time schedule "
    "maintenance, job assignments, village configuration, auth). Employee responses expose "
    "derived **`full_time`** / **`workday`** / **`shift`**; stored schedule rows are maintained "
    "via **`/api/part-time`**. For request/response shapes and error codes see "
    "[developer-guide.md](docs/developer-guide.md)."
)
API_VERSION = _read_project_version()

_BEARER = [{"bearerAuth": []}]

_RESPONSES_DEFAULT = {
    "200": {"description": "Success"},
    "400": {"$ref": "#/components/responses/BadRequest"},
    "401": {"$ref": "#/components/responses/Unauthorized"},
    "403": {"$ref": "#/components/responses/Forbidden"},
    "404": {"$ref": "#/components/responses/NotFound"},
    "409": {"$ref": "#/components/responses/Conflict"},
    "422": {"$ref": "#/components/responses/Unprocessable"},
    "500": {"$ref": "#/components/responses/InternalError"},
}


# ---------------------------------------------------------------------
# Helper: build a $ref content block
# ---------------------------------------------------------------------


def _schema_ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def _content_block(schema_name: str) -> dict:
    return {"application/json": {"schema": _schema_ref(schema_name)}}


def _response_200(schema_name: str, description: str = "OK") -> dict:
    return {"description": description, "content": _content_block(schema_name)}


# ---------------------------------------------------------------------
# Single-operation path fragments
# ---------------------------------------------------------------------


def _op(
    method: str,
    summary: str,
    *,
    tag: str,
    security: list | None = None,
    parameters: list | None = None,
    request_schema: str | None = None,
    response_schema: str | None = None,
    responses: dict | None = None,
) -> dict:
    """Build one OpenAPI ``paths`` operation object (single HTTP method key).

    ``request_schema``  – component schema name for the JSON request body.
    ``response_schema`` – component schema name for the 200 JSON response body.
    ``responses``       – overrides the entire responses block when provided.
    """
    m: dict = {"tags": [tag], "summary": summary}
    if security is not None:
        m["security"] = security
    if parameters:
        m["parameters"] = parameters
    if request_schema is not None:
        m["requestBody"] = {
            "required": True,
            "content": _content_block(request_schema),
        }
    if responses is not None:
        m["responses"] = responses
    else:
        ok: dict = {"description": "OK"}
        if response_schema is not None:
            ok["content"] = _content_block(response_schema)
        m["responses"] = {"200": ok}
    return {method: m}


# ---------------------------------------------------------------------
# Full document assembly
# ---------------------------------------------------------------------


def build_openapi_dict() -> dict:
    """Return OpenAPI 3.0.3 document as a plain ``dict`` (JSON-serializable)."""
    parameters_company_name = [
        {
            "name": "company_name",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
            "description": "Exact company name as stored, e.g. `Bank`.",
        }
    ]
    parameters_employee_number = [
        {
            "name": "employee_number",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
            "description": "Participant employee number (ISO 7064 Mod 97,10 when checksum validation is on).",
        }
    ]
    parameters_job_assignment_number = [
        {
            "name": "job_assignment_number",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
            "description": "Job assignment number (ISO 7064 Mod 97,10 when checksum validation is on).",
        }
    ]
    query_active = [
        {
            "name": "active",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "Filter: `true`/`1`/`yes`, `false`/`0`/`no`, or omit for all.",
        }
    ]
    query_employee_list = query_active + [
        {
            "name": "workday",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
                "default": "all",
                "enum": ["all", "today", *PART_TIME_CALENDAR_WORKDAYS],
            },
            "description": (
                "Part-time list filter and response context (default **`all`**). "
                "Calendar slugs and query-only **`all`** / **`today`** only — aggregate stored slugs "
                "**`weekdays`** and **`all-week`** are **not** valid here (→ `400` **`INVALID_PART_TIME_WORKDAY`**). "
                "**`all`**: no part-time filter; each row's **`workday`** / **`shift`** describe the context day — "
                "full-time participants show **`today`** / **`all-day`**; part-time rows show the matching slot for "
                "**calendar today** in the camp timezone (`general.timezone` in **`village.ini`**, echoed as "
                "**`la-server.camp_timezone`**). **`today`**: only participants with a matching part-time slot for "
                "today's weekday in that timezone (full-time staff excluded); row labels use **`today`**. "
                "A weekday slug (**`monday`** … **`sunday`**): filter to that calendar day (including aggregate "
                "fallback rules) and label rows with that slug. "
                "See [developer-guide.md](docs/developer-guide.md#aggregate-part-time-patterns)."
            ),
        },
        {
            "name": "shift",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["all-day", "morning", "afternoon"],
            },
            "description": (
                "Optional part-time shift filter when **`workday`** is not **`all`**. "
                "Accepted values: **`all-day`**, **`morning`**, **`afternoon`** "
                "(same as **`la-server.part_time_shifts`** in `/api/village-data`). "
                "Ignored when **`workday=all`**. Invalid values → `400` **`INVALID_PART_TIME_SHIFT`**."
            ),
        },
    ]
    query_hard_delete = [
        {
            "name": "hard",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "`true` / `1` / `yes` for permanent delete.",
        }
    ]
    query_part_time_delete = [
        {
            "name": "workday",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
                "enum": PART_TIME_STORED_WORKDAYS,
            },
            "description": (
                "Stored workday slug. When set, delete one row for that key; omit to delete all "
                "part-time rows for the employee (restores full-time when none remain)."
            ),
        }
    ]

    paths: dict[str, dict] = {}

    def merge_path(path: str, fragment: dict) -> None:
        """Merge ``fragment`` (verb → operation) into accumulating ``paths`` map."""
        if path not in paths:
            paths[path] = {}
        for k, v in fragment.items():
            paths[path][k] = v

    # --- Health ---
    merge_path("/api/health", _op("get", "Liveness", tag="Health"))
    merge_path("/api/health/db", _op("get", "Database connectivity", tag="Health"))
    merge_path(
        "/api/health/runtime",
        _op(
            "get",
            "Runtime diagnostics (pool, redacted DB URL, no customer data)",
            tag="Health",
            security=_BEARER,
        ),
    )

    # --- Auth ---
    merge_path(
        "/api/auth/login",
        _op(
            "post",
            "Sign in; returns JWT `token`",
            tag="Authentication",
            security=[],
            request_schema="LoginRequest",
            response_schema="LoginResponse",
            responses={
                "200": _response_200("LoginResponse", "Authenticated"),
                **{
                    k: v
                    for k, v in _RESPONSES_DEFAULT.items()
                    if k in ("400", "401", "404")
                },
            },
        ),
    )
    merge_path(
        "/api/auth/me",
        _op(
            "get",
            "Current employee profile",
            tag="Authentication",
            security=_BEARER,
            response_schema="EmployeeResponse",
        ),
    )
    merge_path(
        "/api/auth/set-auth-group",
        _op(
            "post",
            "Set another user's `auth_group` (admin)",
            tag="Authentication",
            security=_BEARER,
            request_schema="SetAuthGroupRequest",
            response_schema="SetAuthGroupResponse",
        ),
    )
    merge_path(
        "/api/auth/password/set-password",
        _op(
            "post",
            "Change own password",
            tag="Authentication",
            security=_BEARER,
            request_schema="SetPasswordRequest",
        ),
    )
    merge_path(
        "/api/auth/password/reset-password",
        _op(
            "post",
            "Reset participant password (staff or admin)",
            tag="Authentication",
            security=_BEARER,
            request_schema="ResetPasswordRequest",
        ),
    )
    merge_path(
        "/api/auth/refresh",
        _op(
            "post",
            "Issue a new JWT",
            tag="Authentication",
            security=_BEARER,
            response_schema="RefreshResponse",
        ),
    )
    merge_path(
        "/api/auth/logout",
        _op("post", "Logout acknowledgment", tag="Authentication", security=_BEARER),
    )

    # --- Companies ---
    merge_path(
        "/api/companies",
        {
            **_op(
                "get",
                "List companies",
                tag="Companies",
                parameters=query_active,
                response_schema="CompanyListResponse",
            ),
            **_op(
                "post",
                "Create company",
                tag="Companies",
                security=_BEARER,
                request_schema="CreateCompanyRequest",
                response_schema="CompanyResponse",
            ),
        },
    )
    merge_path(
        "/api/companies/{company_name}",
        {
            **_op(
                "get",
                "Get one company",
                tag="Companies",
                parameters=parameters_company_name,
                response_schema="CompanyResponse",
            ),
            **_op(
                "put",
                "Update company",
                tag="Companies",
                security=_BEARER,
                parameters=parameters_company_name,
                request_schema="UpdateCompanyRequest",
                response_schema="CompanyResponse",
            ),
            **_op(
                "delete",
                "Delete company",
                tag="Companies",
                security=_BEARER,
                parameters=parameters_company_name,
            ),
        },
    )

    # --- Employees ---
    merge_path(
        "/api/employees",
        {
            **_op(
                "get",
                "List employees",
                tag="Employees",
                parameters=query_employee_list,
                response_schema="EmployeeListResponse",
            ),
            **_op(
                "post",
                "Create employee (and authentication row)",
                tag="Employees",
                security=_BEARER,
                request_schema="CreateEmployeeRequest",
                response_schema="EmployeeResponse",
            ),
        },
    )
    merge_path(
        "/api/employees/{employee_number}",
        {
            **_op(
                "get",
                "Get one employee",
                tag="Employees",
                parameters=parameters_employee_number,
                response_schema="EmployeeResponse",
            ),
            **_op(
                "put",
                "Update employee",
                tag="Employees",
                security=_BEARER,
                parameters=parameters_employee_number,
                request_schema="UpdateEmployeeRequest",
                response_schema="EmployeeResponse",
            ),
            **_op(
                "delete",
                "Soft or hard delete employee",
                tag="Employees",
                security=_BEARER,
                parameters=parameters_employee_number + query_hard_delete,
            ),
        },
    )

    # --- Part-time (stored schedule rows) ---
    merge_path(
        "/api/part-time/{employee_number}",
        {
            **_op(
                "get",
                "List stored part-time rows",
                tag="Part-time",
                parameters=parameters_employee_number,
                response_schema="ListPartTimesResponse",
                responses={
                    "200": _response_200(
                        "ListPartTimesResponse",
                        "Stored rows ordered by `PART_TIME_STORED_WORKDAYS`",
                    ),
                    **{
                        k: v
                        for k, v in _RESPONSES_DEFAULT.items()
                        if k in ("400", "404")
                    },
                },
            ),
            **_op(
                "post",
                "Create part-time row",
                tag="Part-time",
                security=_BEARER,
                parameters=parameters_employee_number,
                request_schema="CreatePartTimeRequest",
                responses={
                    "201": {
                        "description": "Created",
                        "content": _content_block("PartTimeRowResponse"),
                    },
                    **{
                        k: v
                        for k, v in _RESPONSES_DEFAULT.items()
                        if k in ("400", "401", "403", "404", "409")
                    },
                },
            ),
            **_op(
                "put",
                "Update part-time row (partial)",
                tag="Part-time",
                security=_BEARER,
                parameters=parameters_employee_number,
                request_schema="UpdatePartTimeRequest",
                response_schema="PartTimeRowResponse",
                responses={
                    "200": _response_200("PartTimeRowResponse", "Updated row"),
                    **{
                        k: v
                        for k, v in _RESPONSES_DEFAULT.items()
                        if k in ("400", "401", "403", "404")
                    },
                },
            ),
            **_op(
                "delete",
                "Delete all part-time rows, or one when `?workday=` is set",
                tag="Part-time",
                security=_BEARER,
                parameters=parameters_employee_number + query_part_time_delete,
                responses={
                    "200": {
                        "description": (
                            "All rows deleted (`DeleteAllPartTimesResponse`) or one row "
                            "(`DeleteOnePartTimeResponse` when `?workday=` is set)."
                        ),
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        _schema_ref("DeleteAllPartTimesResponse"),
                                        _schema_ref("DeleteOnePartTimeResponse"),
                                    ]
                                }
                            }
                        },
                    },
                    **{
                        k: v
                        for k, v in _RESPONSES_DEFAULT.items()
                        if k in ("400", "401", "403", "404")
                    },
                },
            ),
        },
    )

    # --- Job assignments ---
    merge_path(
        "/api/job-assignments",
        {
            **_op(
                "get",
                "List job assignments",
                tag="Job assignments",
                response_schema="JobAssignmentListResponse",
            ),
            **_op(
                "post",
                "Create job assignment",
                tag="Job assignments",
                security=_BEARER,
                request_schema="CreateJobAssignmentRequest",
                response_schema="JobAssignmentResponse",
            ),
        },
    )
    merge_path(
        "/api/job-assignments/{job_assignment_number}",
        _op(
            "delete",
            "Remove assignment for employee",
            tag="Job assignments",
            security=_BEARER,
            parameters=parameters_job_assignment_number,
        ),
    )
    merge_path(
        "/api/job-assignments/reset",
        {
            "post": {
                "tags": ["Job assignments"],
                "summary": "Reset assignments (optional `company_name` filter)",
                "security": _BEARER,
                "requestBody": {
                    "required": False,
                    "content": _content_block("ResetJobAssignmentRequest"),
                },
                "responses": {"200": {"description": "OK"}},
            }
        },
    )

    # --- Village ---
    merge_path(
        "/api/village-data",
        {
            "get": {
                "tags": ["Village data"],
                "summary": "Spielstadt config JSON (`village.ini`)",
                "description": (
                    "Loads **`village.ini`** as JSON (one object per section, string-valued keys). "
                    "Typical sections include **`general`**, **`currency`**, **`hourly_pay`**, **`village-images`**, "
                    "and **`village-theme`** (hex UI colors for clients; server does not render them). "
                    "Adds a **`la-server`** object with JWT TTLs, auth groups, part-time enums, camp timezone, "
                    "and employee-number checksum settings."
                ),
                "responses": {
                    "200": {
                        "description": (
                            "`application/json`; includes **`ETag`**. Omit body with matching **`If-None-Match`** is `304`."
                        ),
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/VillageConfig"
                                },
                            },
                        },
                    },
                    "304": {
                        "description": "Not modified; **`If-None-Match`** matched the current **`ETag`**.",
                    },
                    **{
                        k: v
                        for k, v in _RESPONSES_DEFAULT.items()
                        if k in ("404", "500")
                    },
                },
            }
        },
    )
    merge_path("/api/village-data/logo", _op("get", "Logo image", tag="Village data"))
    merge_path(
        "/api/village-data/favicon", _op("get", "Favicon image", tag="Village data")
    )

    return {
        "openapi": "3.0.3",
        "info": {
            "title": API_TITLE,
            "version": API_VERSION,
            "description": API_DESCRIPTION,
        },
        "servers": [
            {
                "url": "/",
                "description": 'Use the same host and port as this server (adjust in Swagger UI "Try it out" if needed).',
            }
        ],
        "tags": [
            {
                "name": "Health",
                "description": "Liveness, database, admin runtime diagnostics",
            },
            {
                "name": "Authentication",
                "description": "JWT sign-in, profile, passwords, refresh, logout",
            },
            {"name": "Companies", "description": "Job-center companies"},
            {
                "name": "Employees",
                "description": (
                    "Camp participants (employees). List supports **`workday`** / **`shift`** filters; "
                    "responses include derived contextual **`full_time`**, **`workday`**, and **`shift`** "
                    "(see **`EmployeeResponse`**). To edit stored schedule rows, use **Part-time** — "
                    "not employee POST/PUT."
                ),
            },
            {
                "name": "Part-time",
                "description": (
                    "Admin CRUD on stored **`part_times`** rows for one employee. "
                    "Returns stored slugs (including aggregates **`weekdays`** / **`all-week`**), not "
                    "contextual **`today`**. Rosters and filters continue to use **Employees**."
                ),
            },
            {
                "name": "Job assignments",
                "description": "Participant–company placements",
            },
            {
                "name": "Village data",
                "description": (
                    "INI-backed Spielstadt branding (name, currency, images, optional **`village-theme`** palette); "
                    "**`/village-data`** adds runtime **`la-server`** metadata."
                ),
            },
        ],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                # ----------------------------------------------------------
                # Auth — request schemas
                # ----------------------------------------------------------
                "LoginRequest": {
                    "type": "object",
                    "required": ["employee_number", "password"],
                    "properties": {
                        "employee_number": {
                            "type": "string",
                            "description": "Participant employee number.",
                            "example": "P00370",
                        },
                        "password": {
                            "type": "string",
                            "description": "Account password.",
                            "example": "secret123",
                        },
                    },
                },
                "SetAuthGroupRequest": {
                    "type": "object",
                    "required": ["employee_number", "auth_group"],
                    "properties": {
                        "employee_number": {
                            "type": "string",
                            "description": "Target participant employee number.",
                            "example": "P00370",
                        },
                        "auth_group": {
                            "type": "string",
                            "description": "New auth group (e.g. `participant`, `staff`, `admin`).",
                            "example": "staff",
                        },
                    },
                },
                "SetPasswordRequest": {
                    "type": "object",
                    "required": ["old_password", "new_password"],
                    "properties": {
                        "old_password": {
                            "type": "string",
                            "description": "Current password for verification.",
                            "example": "oldSecret",
                        },
                        "new_password": {
                            "type": "string",
                            "description": "Desired new password.",
                            "example": "newSecret42",
                        },
                    },
                },
                "ResetPasswordRequest": {
                    "type": "object",
                    "required": ["employee_number"],
                    "properties": {
                        "employee_number": {
                            "type": "string",
                            "description": "Participant whose password should be reset.",
                            "example": "P00370",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Companies — request schemas
                # ----------------------------------------------------------
                "CreateCompanyRequest": {
                    "type": "object",
                    "required": ["company_name", "jobs_max", "hourly_pay"],
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Unique company name.",
                            "example": "Bank",
                        },
                        "jobs_max": {
                            "type": "integer",
                            "description": "Maximum number of simultaneous job slots.",
                            "example": 5,
                        },
                        "hourly_pay": {
                            "type": "number",
                            "description": "Base hourly pay in village currency.",
                            "example": 12.50,
                        },
                        "active": {
                            "type": "boolean",
                            "description": "Whether the company is active (default `true`).",
                            "example": True,
                        },
                        "notes": {
                            "type": "string",
                            "nullable": True,
                            "description": "Optional free-text notes.",
                            "example": "Opens at 9 am.",
                        },
                    },
                },
                "UpdateCompanyRequest": {
                    "type": "object",
                    "description": "Partial update — include only the fields you want to change.",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "New company name.",
                            "example": "Sparkasse",
                        },
                        "jobs_max": {
                            "type": "integer",
                            "description": "New maximum job slots.",
                            "example": 8,
                        },
                        "hourly_pay": {
                            "type": "number",
                            "description": "New hourly pay.",
                            "example": 15.00,
                        },
                        "active": {
                            "type": "boolean",
                            "description": "Activate or deactivate the company.",
                            "example": False,
                        },
                        "notes": {
                            "type": "string",
                            "nullable": True,
                            "description": "Updated notes (send `null` to clear).",
                            "example": "Closed on Wednesdays.",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Employees — request schemas
                # ----------------------------------------------------------
                "CreateEmployeeRequest": {
                    "type": "object",
                    "required": [
                        "first_name",
                        "last_name",
                        "employee_number",
                        "age",
                        "role",
                        "auth_group",
                    ],
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "Participant first name.",
                            "example": "Max",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Participant last name.",
                            "example": "Mustermann",
                        },
                        "employee_number": {
                            "type": "string",
                            "description": "Unique employee number (ISO 7064 Mod 97,10 checksum when validation is on).",
                            "example": "P00370",
                        },
                        "age": {
                            "type": "integer",
                            "description": "Participant age in whole years (non-negative).",
                            "example": 10,
                            "minimum": 0,
                        },
                        "can_leave_alone": {
                            "type": "boolean",
                            "description": "Whether the participant may leave the camp alone (default `true`).",
                            "example": True,
                        },
                        "role": {
                            "type": "string",
                            "description": "Job role description.",
                            "example": "Kassierer",
                        },
                        "auth_group": {
                            "type": "string",
                            "description": "Auth group (e.g. `participant`, `staff`, `admin`).",
                            "example": "participant",
                        },
                        "active": {
                            "type": "boolean",
                            "description": "Whether the employee is active (default `true`).",
                            "example": True,
                        },
                        "notes": {
                            "type": "string",
                            "nullable": True,
                            "description": "Optional free-text notes.",
                            "example": None,
                        },
                    },
                },
                "UpdateEmployeeRequest": {
                    "type": "object",
                    "description": "Partial update — include only the fields you want to change.",
                    "properties": {
                        "first_name": {"type": "string", "example": "Maximilian"},
                        "last_name": {"type": "string", "example": "Muster"},
                        "employee_number": {
                            "type": "string",
                            "description": "New employee number (checksum-validated).",
                            "example": "M00252",
                        },
                        "age": {
                            "type": "integer",
                            "description": "Age in whole years (non-negative).",
                            "example": 12,
                            "minimum": 0,
                        },
                        "can_leave_alone": {"type": "boolean", "example": False},
                        "role": {"type": "string", "example": "Filialleiter"},
                        "active": {"type": "boolean", "example": False},
                        "notes": {
                            "type": "string",
                            "nullable": True,
                            "description": "Updated notes (send `null` to clear).",
                            "example": "Transferred to Bäckerei.",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Job assignments — request schemas
                # ----------------------------------------------------------
                "CreateJobAssignmentRequest": {
                    "type": "object",
                    "required": ["company_name", "employee_number"],
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Exact company name as stored.",
                            "example": "Bank",
                        },
                        "employee_number": {
                            "type": "string",
                            "description": "Participant employee number.",
                            "example": "P00370",
                        },
                    },
                },
                "ResetJobAssignmentRequest": {
                    "type": "object",
                    "description": "Omit body (or send `{}`) to reset all assignments. Provide `company_name` to scope the reset.",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Limit reset to this company only.",
                            "example": "Bank",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Auth — response schemas
                # ----------------------------------------------------------
                "LoginResponse": {
                    "type": "object",
                    "required": [
                        "message",
                        "token",
                        "refresh_token",
                        "auth_group",
                        "password_must_change",
                    ],
                    "properties": {
                        "message": {"type": "string", "example": "Login successful."},
                        "token": {
                            "type": "string",
                            "description": "Short-lived JWT access token.",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "refresh_token": {
                            "type": "string",
                            "description": "Long-lived JWT refresh token.",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "auth_group": {
                            "type": "string",
                            "description": "Auth group of the authenticated user.",
                            "example": "participant",
                        },
                        "password_must_change": {
                            "type": "boolean",
                            "description": "`true` when the user must change their password on next action.",
                            "example": False,
                        },
                    },
                },
                "SetAuthGroupResponse": {
                    "type": "object",
                    "required": ["message", "auth_group", "employee_number"],
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Auth group updated.",
                        },
                        "auth_group": {"type": "string", "example": "staff"},
                        "employee_number": {
                            "type": "string",
                            "example": "P00370",
                        },
                    },
                },
                "RefreshResponse": {
                    "type": "object",
                    "required": ["message", "token", "employee_number"],
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Token refreshed.",
                        },
                        "token": {
                            "type": "string",
                            "description": "New short-lived JWT access token.",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "employee_number": {
                            "type": "string",
                            "example": "P00370",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Companies — response schemas
                # ----------------------------------------------------------
                "CompanyResponse": {
                    "type": "object",
                    "required": [
                        "id",
                        "company_name",
                        "jobs",
                        "hourly_pay",
                        "active",
                        "notes",
                        "created_at",
                        "updated_at",
                    ],
                    "properties": {
                        "id": {"type": "integer", "example": 3},
                        "company_name": {"type": "string", "example": "Bank"},
                        "jobs": {
                            "type": "object",
                            "required": ["available", "max"],
                            "properties": {
                                "available": {
                                    "type": "integer",
                                    "description": "Free job slots (max − assigned).",
                                    "example": 3,
                                },
                                "max": {
                                    "type": "integer",
                                    "description": "Total job slots.",
                                    "example": 5,
                                },
                            },
                        },
                        "hourly_pay": {
                            "type": "number",
                            "description": "Effective hourly pay (base + village bonus).",
                            "example": 14.50,
                        },
                        "active": {"type": "boolean", "example": True},
                        "notes": {"type": "string", "nullable": True, "example": None},
                        "created_at": {
                            "type": "string",
                            "nullable": True,
                            "description": "ISO 8601 creation timestamp.",
                            "example": "2026-05-14T08:00:00",
                        },
                        "updated_at": {
                            "type": "string",
                            "nullable": True,
                            "description": "ISO 8601 last-update timestamp.",
                            "example": "2026-05-14T09:15:00",
                        },
                    },
                },
                "CompanyListResponse": {
                    "type": "array",
                    "items": _schema_ref("CompanyResponse"),
                },
                # ----------------------------------------------------------
                # Employees — response schemas
                # ----------------------------------------------------------
                "EmployeeResponse": {
                    "type": "object",
                    "required": [
                        "id",
                        "first_name",
                        "last_name",
                        "employee_number",
                        "age",
                        "can_leave_alone",
                        "role",
                        "company",
                        "active",
                        "notes",
                        "created_at",
                        "updated_at",
                        "full_time",
                        "workday",
                        "shift",
                    ],
                    "properties": {
                        "id": {"type": "integer", "example": 7},
                        "first_name": {"type": "string", "example": "Max"},
                        "last_name": {"type": "string", "example": "Mustermann"},
                        "employee_number": {
                            "type": "string",
                            "example": "P00370",
                        },
                        "age": {
                            "type": "integer",
                            "description": "Participant age in whole years.",
                            "example": 10,
                            "minimum": 0,
                        },
                        "can_leave_alone": {
                            "type": "boolean",
                            "description": "Whether the participant may leave the camp alone.",
                            "example": True,
                        },
                        "role": {"type": "string", "example": "Kassierer"},
                        "company": {
                            "type": "string",
                            "description": "Company name of current assignment, or empty string.",
                            "example": "Bank",
                        },
                        "active": {"type": "boolean", "example": True},
                        "full_time": {
                            "type": "boolean",
                            "description": (
                                "True when the participant has no `part_times` rows — they work "
                                "Monday through Sunday (every camp day), same calendar coverage as a stored "
                                "`all-week` row but modelled as zero rows with `shift`: `all-day`. "
                                "False when at least one part-time slot exists (may cover only some days, "
                                "e.g. `weekdays` Mon–Fri). Authoritative for distinguishing full-time "
                                "`all-day` from a part-time row stored as `all-day`."
                            ),
                            "example": True,
                        },
                        "workday": {
                            "type": "string",
                            "nullable": True,
                            "enum": [*PART_TIME_API_WORKDAY_LABELS, None],
                            "description": (
                                "Contextual weekday label for the response — never a stored aggregate "
                                "slug (**`weekdays`**, **`all-week`**). "
                                "**Full-time** (`full_time`: true): always the context label (e.g. **`today`** on "
                                "get-one / **`GET /api/auth/me`**). "
                                "**List** (`GET /api/employees`): depends on the **`workday`** query — with default "
                                "**`all`**, calendar **today** in **`la-server.camp_timezone`** → **`today`**; "
                                "with **`workday=tuesday`**, **`tuesday`**. "
                                "**Single** (`GET /api/employees/{employee_number}`) and **`GET /api/auth/me`**: "
                                "calendar today in camp timezone → **`today`** when working that day (ignores list "
                                "query). "
                                "**Part-time**: **`null`** when no `part_times` row applies for the context weekday. "
                                "List **`?workday=`** filters match part-time slots only; full-time rows are excluded "
                                "from filtered lists but show contextual labels when **`workday=all`**. "
                                "Aggregate patterns are listed under **`la-server.part_time_workdays`** for storage "
                                "only; see [developer-guide.md](docs/developer-guide.md#aggregate-part-time-patterns) "
                                "and [database_design.md](docs/database_design.md#aggregate-workdays-weekdays-all-week)."
                            ),
                            "example": "today",
                        },
                        "shift": {
                            "type": "string",
                            "nullable": True,
                            "description": (
                                "Shift on the context **`workday`**: **`all-day`**, **`morning`**, or "
                                "**`afternoon`**. When **`full_time`** is **`true`**, always **`all-day`**. "
                                "**`null`** when **`workday`** is **`null`** (part-time, not scheduled on context day)."
                            ),
                            "example": "all-day",
                        },
                        "notes": {"type": "string", "nullable": True, "example": None},
                        "created_at": {
                            "type": "string",
                            "nullable": True,
                            "example": "2026-05-14T08:00:00",
                        },
                        "updated_at": {
                            "type": "string",
                            "nullable": True,
                            "example": "2026-05-14T09:15:00",
                        },
                        "auth_group": {
                            "type": "string",
                            "nullable": True,
                            "description": "Present on `/auth/me` and admin endpoints; omitted otherwise.",
                            "example": "participant",
                        },
                    },
                },
                "EmployeeListResponse": {
                    "type": "array",
                    "items": _schema_ref("EmployeeResponse"),
                },
                # ----------------------------------------------------------
                # Part-time — request schemas
                # ----------------------------------------------------------
                "CreatePartTimeRequest": {
                    "type": "object",
                    "required": ["workday"],
                    "properties": {
                        "workday": {
                            "type": "string",
                            "enum": PART_TIME_STORED_WORKDAYS,
                            "description": (
                                "Stored schedule key (calendar day or aggregate). "
                                "See **`la-server.part_time_workdays`** on **`GET /api/village-data`**."
                            ),
                            "example": "weekdays",
                        },
                        "shift": {
                            "type": "string",
                            "enum": ["all-day", "morning", "afternoon"],
                            "description": "Defaults to **`all-day`** when omitted.",
                            "example": "morning",
                        },
                        "notes": {
                            "type": "string",
                            "nullable": True,
                            "description": "Optional free-text notes.",
                            "example": None,
                        },
                    },
                },
                "UpdatePartTimeRequest": {
                    "type": "object",
                    "required": ["workday"],
                    "description": (
                        "Partial update. **`workday`** is the lookup key only (not renamable). "
                        "Include **`shift`** and/or **`notes`** to change them."
                    ),
                    "properties": {
                        "workday": {
                            "type": "string",
                            "enum": PART_TIME_STORED_WORKDAYS,
                            "description": "Stored row to update.",
                            "example": "tuesday",
                        },
                        "shift": {
                            "type": "string",
                            "enum": ["all-day", "morning", "afternoon"],
                            "example": "morning",
                        },
                        "notes": {
                            "type": "string",
                            "nullable": True,
                            "description": "Send `null` to clear.",
                            "example": "Covers register until noon.",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Part-time — response schemas
                # ----------------------------------------------------------
                "PartTimeRowResponse": {
                    "type": "object",
                    "required": [
                        "id",
                        "workday",
                        "shift",
                        "notes",
                        "created_at",
                        "updated_at",
                    ],
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "workday": {
                            "type": "string",
                            "enum": PART_TIME_STORED_WORKDAYS,
                            "description": "Stored slug as persisted in `part_times.workday`.",
                            "example": "weekdays",
                        },
                        "shift": {
                            "type": "string",
                            "enum": ["all-day", "morning", "afternoon"],
                            "example": "morning",
                        },
                        "notes": {"type": "string", "nullable": True, "example": None},
                        "created_at": {
                            "type": "string",
                            "nullable": True,
                            "example": "2026-05-14T08:00:00",
                        },
                        "updated_at": {
                            "type": "string",
                            "nullable": True,
                            "example": "2026-05-14T09:15:00",
                        },
                    },
                },
                "ListPartTimesResponse": {
                    "type": "object",
                    "required": ["employee_number", "part_times", "count"],
                    "properties": {
                        "employee_number": {"type": "string", "example": "M00252"},
                        "part_times": {
                            "type": "array",
                            "items": _schema_ref("PartTimeRowResponse"),
                        },
                        "count": {"type": "integer", "example": 1},
                    },
                },
                "DeleteAllPartTimesResponse": {
                    "type": "object",
                    "required": ["message", "count"],
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "part-time rows deleted",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of rows removed (0 when already empty).",
                            "example": 2,
                        },
                    },
                },
                "DeleteOnePartTimeResponse": {
                    "type": "object",
                    "required": ["message"],
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "part-time row deleted",
                        },
                    },
                },
                # ----------------------------------------------------------
                # Job assignments — response schemas
                # ----------------------------------------------------------
                "JobAssignmentResponse": {
                    "type": "object",
                    "required": [
                        "id",
                        "company_id",
                        "employee_id",
                        "job_assignment_number",
                        "notes",
                        "created_at",
                        "updated_at",
                    ],
                    "properties": {
                        "id": {"type": "integer", "example": 12},
                        "company_id": {"type": "integer", "example": 3},
                        "employee_id": {"type": "integer", "example": 7},
                        "job_assignment_number": {
                            "type": "string",
                            "description": "Derived assignment number (ISO 7064 Mod 97,10 checksum).",
                            "example": "*0001263",
                        },
                        "notes": {"type": "string", "nullable": True, "example": None},
                        "created_at": {
                            "type": "string",
                            "nullable": True,
                            "example": "2026-05-14T08:30:00",
                        },
                        "updated_at": {
                            "type": "string",
                            "nullable": True,
                            "example": "2026-05-14T08:30:00",
                        },
                    },
                },
                "JobAssignmentListResponse": {
                    "type": "array",
                    "items": _schema_ref("JobAssignmentResponse"),
                },
                # ----------------------------------------------------------
                # Village data — response schemas
                # ----------------------------------------------------------
                "LAServerRuntime": {
                    "type": "object",
                    "description": (
                        "Runtime metadata appended by LA-Server. Any **`[la-server]`** section "
                        "in **`village.ini`** is discarded and replaced with this block."
                    ),
                    "required": [
                        "auth_groups",
                        "part_time_shifts",
                        "part_time_workdays",
                        "validate_employee_number_checksum",
                        "employee_number_checksum_algorithm",
                        "jwt_access_ttl_minutes",
                        "jwt_refresh_ttl_minutes",
                    ],
                    "properties": {
                        "auth_groups": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Allowed JWT `auth_group` values.",
                        },
                        "part_time_shifts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Allowed `?shift=` values for the employee list endpoint "
                                "(**`all-day`**, **`morning`**, **`afternoon`**). "
                                "Same slugs as stored in `part_times.shift`."
                            ),
                        },
                        "part_time_workdays": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": PART_TIME_STORED_WORKDAYS,
                            },
                            "description": (
                                "Allowed stored `part_times.workday` values: calendar days "
                                "**`monday`** … **`sunday`**, plus aggregate patterns **`weekdays`** (Mon–Fri) "
                                "and **`all-week`** (Mon–Sun). Storage and data entry only — employee list "
                                "**`?workday=`** filters and response **`workday`** labels never use aggregate "
                                "slugs. Full precedence and pairing rules: "
                                "[developer-guide.md](docs/developer-guide.md#aggregate-part-time-patterns) "
                                "(data entry, before/after examples) and "
                                "[database_design.md](docs/database_design.md#aggregate-workdays-weekdays-all-week) "
                                "(precedence)."
                            ),
                        },
                        "validate_employee_number_checksum": {
                            "type": "boolean",
                            "description": "Whether employee numbers must pass ISO 7064 Mod 97,10 checksum validation.",
                        },
                        "employee_number_checksum_algorithm": {
                            "type": "string",
                            "nullable": True,
                            "description": "`ISO_7064_MOD_97_10` when validation is on; `null` when off.",
                            "example": "ISO_7064_MOD_97_10",
                        },
                        "jwt_access_ttl_minutes": {
                            "type": "integer",
                            "description": "Access JWT lifetime from server config.",
                            "minimum": 0,
                        },
                        "jwt_refresh_ttl_minutes": {
                            "type": "integer",
                            "description": "Refresh JWT lifetime in minutes from server config.",
                            "minimum": 0,
                        },
                        "camp_timezone": {
                            "type": "string",
                            "description": (
                                "IANA time zone used for camp calendar-day logic (from **`general.timezone`** in "
                                "**`village.ini`**, with server fallback when missing or invalid). Drives "
                                '**`workday=today`** on employee lists and **`workday`: `"today"`** on employee '
                                "responses. Same identifiers as Python **`zoneinfo`** (e.g. `Europe/Berlin`)."
                            ),
                            "example": "Europe/Berlin",
                        },
                    },
                },
                "VillageConfig": {
                    "type": "object",
                    "required": ["la-server"],
                    "properties": {
                        "la-server": {"$ref": "#/components/schemas/LAServerRuntime"}
                    },
                    "additionalProperties": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "One object per **`village.ini`** section (string keys to string values).",
                    },
                    "description": (
                        "**`village.ini`** as nested maps (string keys and values per section), "
                        "plus **`la-server`** injected at runtime. "
                        "Optional **`village-theme`** carries hex colors for client UIs only. "
                        "Responses include an **`ETag`** header; repeat with **`If-None-Match`** for `304 Not Modified`."
                    ),
                },
                # ----------------------------------------------------------
                # Shared error schema
                # ----------------------------------------------------------
                "ErrorBody": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
            },
            "responses": {
                "BadRequest": {
                    "description": "Validation or bad input",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
                "Unauthorized": {
                    "description": "Missing or expired JWT",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
                "Forbidden": {
                    "description": "Insufficient `auth_group`",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
                "NotFound": {
                    "description": "Resource not found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
                "Conflict": {
                    "description": "Constraint violation",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
                "Unprocessable": {
                    "description": "Invalid JWT format (library)",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
                "InternalError": {
                    "description": "Server or database error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorBody"}
                        }
                    },
                },
            },
        },
    }
