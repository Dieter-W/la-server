"""Auto-computed API and database schema compatibility hashes.

Hashes are deterministic 16-character hex prefixes of SHA-256 digests over
canonical JSON (``sort_keys=True``, ``separators=(",", ":")``). OpenAPI
**structure** changes and model/table/column changes update the relevant hash;
documentation-only OpenAPI fields (``description``, ``summary``, ``example``,
etc.) do not.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from functools import lru_cache
from typing import Any

from sqlalchemy.schema import (
    CheckConstraint,
    ColumnDefault,
    DefaultClause,
    ForeignKeyConstraint,
    UniqueConstraint,
)

from app.database import db
from app.openapi_spec import build_openapi_dict

# ---------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------

_HASH_HEX_LENGTH = 16

_SCHEMA_REF_RE = re.compile(r"^#/components/schemas/(.+)$")
_RESPONSE_REF_RE = re.compile(r"^#/components/responses/(.+)$")

# API resource key → path prefix under ``paths`` (each key collects paths via ``startswith``).
_API_RESOURCE_PATH_PREFIXES: dict[str, str] = {
    "auth": "/api/auth",
    "employees": "/api/employees",
    "companies": "/api/companies",
    "part_time": "/api/part-time",
    "company_jobs_max": "/api/company-jobs-max",
    "job_assignments": "/api/job-assignments",
    "job_assignment_history": "/api/job-assignment-history",
    "attendance": "/api/attendance",
    "village_data": "/api/village-data",
    "health": "/api/health",
    "version": "/api/version",
}

# Tables excluded from schema contract hashing (stores applied hashes, not business data).
_SCHEMA_HASH_EXCLUDED_TABLES = frozenset({"schema_metadata"})

# OpenAPI keys omitted from contract hashing (documentation / organization only).
_OPENAPI_DOC_ONLY_KEYS = frozenset(
    {
        "description",
        "summary",
        "example",
        "examples",
        "externalDocs",
    }
)

_HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
)


def _canonical_hash(data: dict) -> str:
    """Return a stable short hex digest for ``data``."""
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_HASH_HEX_LENGTH]


# ---------------------------------------------------------------------
# OpenAPI slice helpers
# ---------------------------------------------------------------------


def _openapi_structure_only(
    obj: Any,
    *,
    in_operation: bool = False,
    in_schema: bool = False,
) -> Any:
    """Return an OpenAPI fragment with documentation-only keys removed."""
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for key, value in obj.items():
            if key in _OPENAPI_DOC_ONLY_KEYS:
                continue
            if key == "tags" and in_operation:
                continue
            if key == "title" and in_schema:
                continue

            child_in_operation = in_operation or key in _HTTP_METHODS
            child_in_schema = in_schema or key == "schema"

            if key == "schemas" and isinstance(value, dict):
                cleaned[key] = {
                    name: _openapi_structure_only(body, in_schema=True)
                    for name, body in value.items()
                }
                continue

            if key in ("properties", "patternProperties") and isinstance(value, dict):
                cleaned[key] = {
                    prop_name: _openapi_structure_only(prop_value, in_schema=True)
                    for prop_name, prop_value in value.items()
                }
                continue

            cleaned[key] = _openapi_structure_only(
                value,
                in_operation=child_in_operation,
                in_schema=child_in_schema,
            )
        return cleaned
    if isinstance(obj, list):
        return [
            _openapi_structure_only(
                item, in_operation=in_operation, in_schema=in_schema
            )
            for item in obj
        ]
    return obj


def _walk_refs(obj: Any, schema_refs: set[str], response_refs: set[str]) -> None:
    """Collect ``components/schemas`` and ``components/responses`` refs from a fragment."""
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if isinstance(ref, str):
            schema_match = _SCHEMA_REF_RE.match(ref)
            if schema_match:
                schema_refs.add(schema_match.group(1))
            else:
                response_match = _RESPONSE_REF_RE.match(ref)
                if response_match:
                    response_refs.add(response_match.group(1))
        for value in obj.values():
            _walk_refs(value, schema_refs, response_refs)
    elif isinstance(obj, list):
        for item in obj:
            _walk_refs(item, schema_refs, response_refs)


def _expand_schema_closure(
    all_schemas: dict[str, Any], seed_names: set[str]
) -> dict[str, Any]:
    """Return ``seed_names`` plus any schemas reachable via ``$ref`` (transitive)."""
    names: set[str] = set()
    pending = set(seed_names)
    while pending:
        name = pending.pop()
        if name in names or name not in all_schemas:
            continue
        names.add(name)
        nested: set[str] = set()
        nested_responses: set[str] = set()
        _walk_refs(all_schemas[name], nested, nested_responses)
        pending.update(nested - names)
    return {name: all_schemas[name] for name in sorted(names)}


def _paths_for_resource(openapi: dict[str, Any], path_prefix: str) -> dict[str, Any]:
    """Collect ``paths`` entries whose key starts with ``path_prefix``."""
    paths = openapi.get("paths", {})
    return {key: paths[key] for key in sorted(paths) if key.startswith(path_prefix)}


def _openapi_slice_for_resource(
    openapi: dict[str, Any], resource_key: str, *, method: str | None = None
) -> dict:
    """Build the canonical JSON subset hashed for one API resource group."""
    path_prefix = _API_RESOURCE_PATH_PREFIXES[resource_key]
    paths = _paths_for_resource(openapi, path_prefix)
    if method is not None:
        paths = {
            path: {
                key: value
                for key, value in item.items()
                if key == method or key not in _HTTP_METHODS
            }
            for path, item in paths.items()
            if method in item
        }

    schema_refs: set[str] = set()
    response_refs: set[str] = set()
    for path_item in paths.values():
        _walk_refs(path_item, schema_refs, response_refs)

    all_responses = openapi.get("components", {}).get("responses", {})
    resolved_responses: dict[str, Any] = {}
    pending = set(response_refs)
    while pending:
        name = pending.pop()
        body = all_responses.get(name)
        if body is None or name in resolved_responses:
            continue
        resolved_responses[name] = body
        nested_schemas: set[str] = set()
        nested_responses: set[str] = set()
        _walk_refs(body, nested_schemas, nested_responses)
        schema_refs |= nested_schemas
        pending |= nested_responses - set(resolved_responses)

    all_schemas = openapi.get("components", {}).get("schemas", {})
    schemas = _expand_schema_closure(all_schemas, schema_refs)
    return _openapi_structure_only(
        {
            "paths": paths,
            "schemas": schemas,
            "responses": dict(sorted(resolved_responses.items())),
        }
    )


@lru_cache(maxsize=1)
def _build_openapi_dict_cached() -> dict:
    """Memoize ``build_openapi_dict()`` for repeated hash computation."""
    return build_openapi_dict()


def _cached_openapi_dict() -> dict:
    """Return an independent copy of the memoized OpenAPI document."""
    return copy.deepcopy(_build_openapi_dict_cached())


@lru_cache(maxsize=1)
def compute_api_compatibility_hashes() -> dict[str, str]:
    """Return one compatibility hash per documented API resource group."""
    openapi = _build_openapi_dict_cached()
    return {
        resource_key: _canonical_hash(
            _openapi_slice_for_resource(openapi, resource_key)
        )
        for resource_key in _API_RESOURCE_PATH_PREFIXES
    }


@lru_cache(maxsize=1)
def compute_api_method_compatibility_hashes() -> dict[str, dict[str, str]]:
    """Return one compatibility hash per API resource group and HTTP method."""
    openapi = _build_openapi_dict_cached()
    result: dict[str, dict[str, str]] = {}
    for resource_key, path_prefix in _API_RESOURCE_PATH_PREFIXES.items():
        paths = _paths_for_resource(openapi, path_prefix)
        methods = sorted(
            {key for item in paths.values() for key in item if key in _HTTP_METHODS}
        )
        result[resource_key] = {
            method: _canonical_hash(
                _openapi_slice_for_resource(openapi, resource_key, method=method)
            )
            for method in methods
        }
    return result


# ---------------------------------------------------------------------
# SQLAlchemy schema helpers
# ---------------------------------------------------------------------


def _serialize_column_default(default: Any) -> Any | None:
    """Return a JSON-safe default when it is schema-level (non-callable)."""
    if default is None:
        return None
    if isinstance(default, ColumnDefault):
        if default.is_callable or default.is_scalar is False:
            return None
        return str(default.arg)
    if isinstance(default, DefaultClause):
        if default.is_callable:
            return None
        return str(default.arg)
    if callable(default):
        return None
    return str(default)


def _column_descriptor(column: Any) -> dict[str, Any]:
    """Build a deterministic column record for hashing."""
    return {
        "name": column.name,
        "type": str(column.type),
        "nullable": column.nullable,
        "primary_key": bool(column.primary_key),
        "default": _serialize_column_default(column.default),
        "server_default": _serialize_column_default(column.server_default),
    }


def _foreign_key_descriptor(fk: ForeignKeyConstraint) -> dict[str, Any]:
    """Build a deterministic foreign-key record for hashing."""
    referred = fk.elements[0].column.table.name if fk.elements else None
    referred_columns = [element.column.name for element in fk.elements]
    entry: dict[str, Any] = {
        "columns": list(fk.columns.keys()),
        "referred_table": referred,
        "referred_columns": referred_columns,
    }
    ondelete = fk.ondelete
    if ondelete is not None:
        entry["ondelete"] = ondelete
    return entry


def _table_contract_descriptor(table: Any) -> dict[str, Any]:
    """Build the canonical JSON subset hashed for one database table."""
    columns = sorted(
        (_column_descriptor(column) for column in table.columns),
        key=lambda item: item["name"],
    )

    foreign_keys = sorted(
        (
            _foreign_key_descriptor(constraint)
            for constraint in table.constraints
            if isinstance(constraint, ForeignKeyConstraint)
        ),
        key=lambda item: (item["referred_table"], tuple(item["columns"])),
    )

    unique_constraints = sorted(
        {
            tuple(sorted(constraint.columns.keys()))
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
    )

    indexes = sorted(
        (
            {
                "columns": [column.name for column in index.columns],
                "unique": bool(index.unique),
            }
            for index in table.indexes
        ),
        key=lambda item: (tuple(item["columns"]), item["unique"]),
    )

    check_constraints = sorted(
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    )

    primary_key = [column.name for column in table.primary_key.columns]

    return {
        "columns": columns,
        "foreign_keys": foreign_keys,
        "unique_constraints": [list(names) for names in unique_constraints],
        "indexes": indexes,
        "primary_key": primary_key,
        "check_constraints": check_constraints,
    }


@lru_cache(maxsize=1)
def compute_schema_compatibility_hashes() -> dict[str, str]:
    """Return one compatibility hash per business database table (excluding ``schema_metadata``)."""
    import app.models  # noqa: F401 — register models on metadata

    metadata = db.metadata
    table_names = sorted(
        name for name in metadata.tables if name not in _SCHEMA_HASH_EXCLUDED_TABLES
    )
    return {
        table_name: _canonical_hash(
            _table_contract_descriptor(metadata.tables[table_name])
        )
        for table_name in table_names
    }
