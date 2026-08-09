"""Golden tests for auto-computed API and schema compatibility hashes."""

import copy

from app.contract_version import (
    _API_RESOURCE_PATH_PREFIXES,
    _build_openapi_dict_cached,
    _canonical_hash,
    _openapi_slice_for_resource,
    _openapi_structure_only,
    _paths_for_resource,
    _table_contract_descriptor,
    _walk_refs,
    compute_api_compatibility_hashes,
    compute_schema_compatibility_hashes,
)
from app.version import SERVER_VERSION, load_committed_hashes

_committed_hashes = load_committed_hashes()
COMMITTED_API_COMPATIBILITY_HASHES = _committed_hashes["api_compatibility_hashes"]
COMMITTED_SCHEMA_COMPATIBILITY_HASHES = _committed_hashes["schema_compatibility_hashes"]


def test_api_compatibility_hashes_match_committed_baseline():
    """Each API resource group hash matches the committed baseline."""
    assert compute_api_compatibility_hashes() == COMMITTED_API_COMPATIBILITY_HASHES


def test_schema_compatibility_hashes_match_committed_baseline():
    """Each database table hash matches the committed baseline."""
    assert (
        compute_schema_compatibility_hashes() == COMMITTED_SCHEMA_COMPATIBILITY_HASHES
    )


def test_version_endpoint_returns_compatibility_hashes(client):
    """GET /api/version exposes release tag and both compatibility hash maps."""
    response = client.get("/api/version")
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.get_json()
    assert data["server_version"] == SERVER_VERSION
    assert data["api_compatibility_hashes"] == COMMITTED_API_COMPATIBILITY_HASHES
    assert data["schema_compatibility_hashes"] == COMMITTED_SCHEMA_COMPATIBILITY_HASHES


def test_api_hashes_cover_all_resource_groups():
    """Hash map keys match the documented API resource groups."""
    assert set(compute_api_compatibility_hashes()) == set(_API_RESOURCE_PATH_PREFIXES)


def test_every_openapi_path_matches_exactly_one_resource_prefix():
    """Each documented path belongs to one API resource group (no unhashed endpoints)."""
    from app.contract_version import _cached_openapi_dict

    openapi = _cached_openapi_dict()
    prefixes = list(_API_RESOURCE_PATH_PREFIXES.values())

    for path in openapi.get("paths", {}):
        matches = [prefix for prefix in prefixes if path.startswith(prefix)]
        assert len(matches) == 1, f"{path!r} matched {matches!r}"


def _api_hashes_for_openapi(openapi) -> dict[str, str]:
    """Recompute per-resource API hashes from an OpenAPI document copy."""
    return {
        resource_key: _canonical_hash(
            _openapi_slice_for_resource(openapi, resource_key)
        )
        for resource_key in _API_RESOURCE_PATH_PREFIXES
    }


def _resources_referencing_response(openapi, response_name: str) -> set[str]:
    """Return resource keys whose path slice transitively references a shared response."""
    referencing: set[str] = set()
    for resource_key, path_prefix in _API_RESOURCE_PATH_PREFIXES.items():
        paths = _paths_for_resource(openapi, path_prefix)
        schema_refs: set[str] = set()
        response_refs: set[str] = set()
        for path_item in paths.values():
            _walk_refs(path_item, schema_refs, response_refs)
        if response_name in response_refs:
            referencing.add(resource_key)
    return referencing


def test_shared_response_body_mutation_changes_dependent_resource_hashes():
    """A structural change to a shared response body updates every referencing resource hash."""
    from app.contract_version import _cached_openapi_dict

    openapi = _cached_openapi_dict()
    before = _api_hashes_for_openapi(openapi)
    referencing = _resources_referencing_response(openapi, "Unauthorized")
    assert referencing

    unauthorized = openapi["components"]["responses"]["Unauthorized"]
    json_content = unauthorized["content"]["application/json"]
    json_content["schema"] = {
        "type": "object",
        "required": ["error", "_contract_test_field"],
        "properties": {
            "error": {"type": "string"},
            "_contract_test_field": {"type": "string"},
        },
    }

    after = _api_hashes_for_openapi(openapi)

    for resource_key in referencing:
        assert after[resource_key] != before[resource_key], resource_key
    for resource_key in set(_API_RESOURCE_PATH_PREFIXES) - referencing:
        assert after[resource_key] == before[resource_key], resource_key


def test_server_version_patch_leaves_village_data_and_version_hashes_stable(
    monkeypatch,
):
    """Release tag churn in examples/runtime docs must not move village_data or version hashes."""
    from app.contract_version import _cached_openapi_dict

    openapi_before = _cached_openapi_dict()
    before = {
        resource_key: _canonical_hash(
            _openapi_slice_for_resource(openapi_before, resource_key)
        )
        for resource_key in ("village_data", "version")
    }

    monkeypatch.setattr("app.openapi_spec.SERVER_VERSION", "9.9.9-patched")
    _build_openapi_dict_cached.cache_clear()
    compute_api_compatibility_hashes.cache_clear()

    openapi_after = _build_openapi_dict_cached()
    after = {
        resource_key: _canonical_hash(
            _openapi_slice_for_resource(openapi_after, resource_key)
        )
        for resource_key in ("village_data", "version")
    }

    assert after == before


def test_schema_property_named_description_survives_structure_stripping():
    """Property keys named ``description`` are schema fields, not documentation-only keys."""
    fragment = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Human-readable text for this row.",
            }
        },
    }

    stripped = _openapi_structure_only(fragment, in_schema=True)

    assert "description" in stripped["properties"]
    assert stripped["properties"]["description"] == {"type": "string"}


def test_openapi_structure_only_strips_documentation_keys():
    """Documentation-only OpenAPI fields are removed before hashing."""
    fragment = {
        "paths": {
            "/api/employees": {
                "get": {
                    "tags": ["Employees"],
                    "summary": "List employees",
                    "description": "Returns all employees.",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "title": "EmployeeList",
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Full name",
                                                "example": "Ada",
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
        "schemas": {
            "Employee": {
                "title": "Employee",
                "type": "object",
                "description": "An employee row.",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                },
            }
        },
    }

    stripped = _openapi_structure_only(fragment)

    get_op = stripped["paths"]["/api/employees"]["get"]
    assert "tags" not in get_op
    assert "summary" not in get_op
    assert "description" not in get_op

    schema = get_op["responses"]["200"]["content"]["application/json"]["schema"]
    assert "title" not in schema
    assert "description" not in schema["properties"]["name"]
    assert "example" not in schema["properties"]["name"]

    assert "title" not in stripped["schemas"]["Employee"]
    assert "description" not in stripped["schemas"]["Employee"]
    assert "example" not in stripped["schemas"]["Employee"]["properties"]["id"]


def test_documentation_only_openapi_changes_do_not_change_api_hashes():
    """Mutating descriptions/summaries/examples alone leaves compatibility hashes stable."""
    from app.contract_version import _cached_openapi_dict

    openapi = _cached_openapi_dict()
    paths = openapi["paths"]
    first_path = next(iter(paths.values()))
    first_op = next(iter(first_path.values()))
    first_op["description"] = "Mutated description for hash stability test"
    first_op["summary"] = "Mutated summary"
    first_op["tags"] = ["MutatedTag"]

    schemas = openapi.get("components", {}).get("schemas", {})
    if schemas:
        first_schema = next(iter(schemas.values()))
        first_schema["description"] = "Mutated schema description"
        first_schema["title"] = "MutatedTitle"
        properties = first_schema.get("properties")
        if isinstance(properties, dict) and properties:
            next(iter(properties.values()))["example"] = "mutated-example"

    before = compute_api_compatibility_hashes()
    after = {
        resource_key: _canonical_hash(
            _openapi_slice_for_resource(openapi, resource_key)
        )
        for resource_key in _API_RESOURCE_PATH_PREFIXES
    }
    assert after == before


def test_structural_openapi_changes_change_resource_hash():
    """Adding a required response field changes only the affected resource hash."""
    from app.contract_version import _cached_openapi_dict

    openapi = _cached_openapi_dict()
    before = compute_api_compatibility_hashes()

    employees_paths = {
        key: value
        for key, value in openapi["paths"].items()
        if key.startswith("/api/employees")
    }
    assert employees_paths
    first_path_item = next(iter(employees_paths.values()))
    first_op = next(iter(first_path_item.values()))
    responses = first_op.setdefault("responses", {})
    ok = responses.setdefault("200", {"description": "OK"})
    content = ok.setdefault("content", {})
    json_content = content.setdefault("application/json", {})
    schema = json_content.setdefault("schema", {"type": "object", "properties": {}})
    schema.setdefault("properties", {})["_contract_test_field"] = {"type": "string"}
    required = schema.setdefault("required", [])
    if "_contract_test_field" not in required:
        required.append("_contract_test_field")

    after = {
        resource_key: _canonical_hash(
            _openapi_slice_for_resource(openapi, resource_key)
        )
        for resource_key in _API_RESOURCE_PATH_PREFIXES
    }

    assert after["employees"] != before["employees"]
    unchanged = {key: value for key, value in before.items() if key != "employees"}
    assert {key: after[key] for key in unchanged} == unchanged


def test_structural_model_changes_change_table_hash():
    """Adding a column to one table descriptor changes only that table's schema hash."""
    import app.models  # noqa: F401 — register models on metadata
    from app.database import db

    before = compute_schema_compatibility_hashes()
    employees_table = db.metadata.tables["employees"]
    descriptor = copy.deepcopy(_table_contract_descriptor(employees_table))
    descriptor["columns"].append(
        {
            "name": "_contract_test_column",
            "type": "VARCHAR(1)",
            "nullable": True,
            "primary_key": False,
            "default": None,
            "server_default": None,
        }
    )
    after = dict(before)
    after["employees"] = _canonical_hash(descriptor)

    assert after["employees"] != before["employees"]
    unchanged = {key: value for key, value in before.items() if key != "employees"}
    assert {key: after[key] for key in unchanged} == unchanged


def test_index_rename_does_not_change_table_hash():
    """Index object names are excluded from the schema contract descriptor."""
    import app.models  # noqa: F401 — register models on metadata
    from app.database import db

    table = db.metadata.tables["attendances"]
    hash_before = _canonical_hash(_table_contract_descriptor(table))

    for entry in _table_contract_descriptor(table)["indexes"]:
        assert set(entry) == {"columns", "unique"}

    indexes = list(table.indexes)
    original_names = [index.name for index in indexes]
    try:
        for index in indexes:
            index.name = f"renamed_{index.name}"
        hash_after = _canonical_hash(_table_contract_descriptor(table))
    finally:
        for index, name in zip(indexes, original_names, strict=True):
            index.name = name

    assert hash_after == hash_before


def test_server_default_change_changes_table_hash():
    """``server_default`` is part of the schema contract and affects the table hash."""
    import app.models  # noqa: F401 — register models on metadata
    from app.database import db

    before = compute_schema_compatibility_hashes()
    employees_table = db.metadata.tables["employees"]
    descriptor = copy.deepcopy(_table_contract_descriptor(employees_table))
    descriptor["columns"][0]["server_default"] = "'contract-test-default'"

    after = dict(before)
    after["employees"] = _canonical_hash(descriptor)

    assert after["employees"] != before["employees"]
    unchanged = {key: value for key, value in before.items() if key != "employees"}
    assert {key: after[key] for key in unchanged} == unchanged
