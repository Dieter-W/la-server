"""Regenerate or verify ``app/compatibility_hashes.json`` against computed hashes."""

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.contract_version import (
    compute_api_compatibility_hashes,
    compute_api_method_compatibility_hashes,
    compute_schema_compatibility_hashes,
)

HASHES_PATH = project_root / "app" / "compatibility_hashes.json"


def compute_hashes() -> dict[str, dict]:
    return {
        "api_compatibility_hashes": compute_api_compatibility_hashes(),
        "api_method_compatibility_hashes": compute_api_method_compatibility_hashes(),
        "schema_compatibility_hashes": compute_schema_compatibility_hashes(),
    }


def format_hashes(payload: dict[str, dict]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def load_file_hashes() -> dict[str, dict] | None:
    if not HASHES_PATH.is_file():
        return None
    with open(HASHES_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_hashes(payload: dict[str, dict]) -> None:
    HASHES_PATH.write_text(format_hashes(payload), encoding="utf-8")


def check_hashes() -> int:
    computed = compute_hashes()
    committed = load_file_hashes()
    if committed == computed:
        print(f"{HASHES_PATH} is up to date")
        return 0

    print(f"{HASHES_PATH} is out of date")
    print("--- committed")
    print(format_hashes(committed or {}), end="")
    print("--- computed")
    print(format_hashes(computed), end="")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update or verify app/compatibility_hashes.json",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="exit 1 and print diff when the file differs from computed hashes",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="write computed hashes to app/compatibility_hashes.json",
    )
    args = parser.parse_args()

    if args.write:
        write_hashes(compute_hashes())
        print(f"Wrote {HASHES_PATH}")
        return 0

    return check_hashes()


if __name__ == "__main__":
    sys.exit(main())
