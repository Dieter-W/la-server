"""OpenAPI 3.0 schema for the LA-Server REST API. Narrative docs: docs/developer-guide.md."""

API_TITLE = "LA-Server API"
API_DESCRIPTION = (
    "Kinderspielstadt Los Ämmerles JSON REST API (companies, employees, job assignments, "
    "village configuration, auth). For request/response shapes and error codes see "
    "[developer-guide.md](docs/developer-guide.md)."
)
API_VERSION = "0.5.0"

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


def _op(
    method: str,
    summary: str,
    *,
    tag: str,
    security: list | None = None,
    parameters: list | None = None,
    request_body: bool = False,
    responses: dict | None = None,
) -> dict:
    m: dict = {"tags": [tag], "summary": summary}
    if security is not None:
        m["security"] = security
    if parameters:
        m["parameters"] = parameters
    if request_body:
        m["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object", "additionalProperties": True}
                }
            },
        }
    m["responses"] = responses or {"200": {"description": "OK"}}
    return {method: m}


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
    query_active = [
        {
            "name": "active",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "Filter: `true`/`1`/`yes`, `false`/`0`/`no`, or omit for all.",
        }
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

    paths: dict[str, dict] = {}

    def merge_path(path: str, fragment: dict) -> None:
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
            request_body=True,
            responses={
                "200": {"description": "Authenticated"},
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
        _op("get", "Current employee profile", tag="Authentication", security=_BEARER),
    )
    merge_path(
        "/api/auth/set-auth-group",
        _op(
            "post",
            "Set another user’s `auth_group` (admin)",
            tag="Authentication",
            security=_BEARER,
            request_body=True,
        ),
    )
    merge_path(
        "/api/auth/password/set-password",
        _op(
            "post",
            "Change own password",
            tag="Authentication",
            security=_BEARER,
            request_body=True,
        ),
    )
    merge_path(
        "/api/auth/password/reset-password",
        _op(
            "post",
            "Reset participant password (staff or admin)",
            tag="Authentication",
            security=_BEARER,
            request_body=True,
        ),
    )
    merge_path(
        "/api/auth/refresh",
        _op("post", "Issue a new JWT", tag="Authentication", security=_BEARER),
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
            ),
            **_op(
                "post",
                "Create company",
                tag="Companies",
                security=_BEARER,
                request_body=True,
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
            ),
            **_op(
                "put",
                "Update company",
                tag="Companies",
                security=_BEARER,
                parameters=parameters_company_name,
                request_body=True,
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
                parameters=query_active,
            ),
            **_op(
                "post",
                "Create employee (and authentication row)",
                tag="Employees",
                security=_BEARER,
                request_body=True,
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
            ),
            **_op(
                "put",
                "Update employee",
                tag="Employees",
                security=_BEARER,
                parameters=parameters_employee_number,
                request_body=True,
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

    # --- Job assignments ---
    merge_path(
        "/api/job-assignments",
        {
            **_op("get", "List job assignments", tag="Job assignments"),
            **_op(
                "post",
                "Create job assignment",
                tag="Job assignments",
                security=_BEARER,
                request_body=True,
            ),
        },
    )
    merge_path(
        "/api/job-assignments/{employee_number}",
        _op(
            "delete",
            "Remove assignment for employee",
            tag="Job assignments",
            security=_BEARER,
            parameters=parameters_employee_number,
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
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"company_name": {"type": "string"}},
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "OK"}},
            }
        },
    )

    # --- Village ---
    merge_path(
        "/api/village-data",
        _op("get", "Spielstadt config JSON (`village.ini`)", tag="Village data"),
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
                "description": "Use the same host and port as this server (adjust in Swagger UI “Try it out” if needed).",
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
            {"name": "Employees", "description": "Camp participants (employees)"},
            {
                "name": "Job assignments",
                "description": "Participant–company placements",
            },
            {"name": "Village data", "description": "INI-backed Spielstadt branding"},
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
                "ErrorBody": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                    },
                }
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
