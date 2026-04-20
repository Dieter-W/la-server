#!/usr/bin/env bash
# LA-Server production setup (no Poetry). Same behavior as scripts/setup.ps1.
#
# Usage:
#   ./scripts/setup.sh [--mode init-env|provision] [--requirements-path PATH]
#                        [--skip-create-database] [--force-recreate-venv]
#   ./scripts/setup.sh -h|--help
#
# Defaults: --mode init-env, --requirements-path ./data/requirements.txt (relative to project root)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
ENV_EXAMPLE_PATH="$PROJECT_ROOT/.env.example"
ENV_PATH="$PROJECT_ROOT/.env"
REPO_REQUIREMENTS_PATH="$PROJECT_ROOT/data/requirements.txt"

MODE="init-env"
REQUIREMENTS_PATH="./data/requirements.txt"
SKIP_CREATE_DATABASE=0
FORCE_RECREATE_VENV=0

usage() {
  cat <<EOF
LA-Server production setup (same as scripts/setup.ps1).

Options:
  --mode <init-env|provision>   init-env: create .env from .env.example (default). provision: full setup.
  --requirements-path <path>    requirements file (default: ./data/requirements.txt from project root).
  --skip-create-database        Do not run scripts/create_database.py in provision mode.
  --force-recreate-venv         Remove .venv and recreate it before installing dependencies.
  -h, --help                    Show this help.

Examples:
  ./scripts/setup.sh --mode init-env
  ./scripts/setup.sh --mode provision
  ./scripts/setup.sh --mode provision --skip-create-database
  ./scripts/setup.sh --mode provision --force-recreate-venv --requirements-path ./data/requirements.txt
EOF
}

resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  else
    echo ""
  fi
}

require_python_314() {
  local py="$1"
  if ! "$py" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)' 2>/dev/null; then
    local ver
    ver="$("$py" --version 2>&1 || true)"
    echo "Python 3.14 or higher is required. Found: $ver" >&2
    exit 1
  fi
}

resolve_requirements_file() {
  local candidate="$1"
  local fallback="$2"
  if [[ -f "$candidate" ]]; then
    python -c "import os, sys; print(os.path.abspath(sys.argv[1]))" "$candidate"
    return 0
  fi
  if [[ -f "$fallback" ]]; then
    echo "Requirements not found at '$candidate'. Falling back to '$fallback'." >&2
    echo "$fallback"
    return 0
  fi
  echo "Requirements file not found. Checked '$candidate' and '$fallback'." >&2
  exit 1
}

# Returns 0 (true) if .env is considered customized for provision; 1 (false) otherwise.
# Mirrors scripts/setup.ps1 Test-EnvCustomized.
env_is_customized() {
  local env_file="$1"
  local example_file="$2"
  if [[ ! -f "$env_file" ]]; then
    return 1
  fi
  if [[ ! -f "$example_file" ]]; then
    return 0
  fi
  if cmp -s "$env_file" "$example_file"; then
    return 1
  fi
  local still_using_placeholders=false
  if ! grep -qF "SECRET_KEY=your-secret-key-here" "$env_file"; then
    still_using_placeholders=true
  fi
  if ! grep -qF "MARIADB_PASSWORD=your-password" "$env_file"; then
    still_using_placeholders=true
  fi
  if [[ "$still_using_placeholders" == true ]]; then
    return 0
  fi
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --requirements-path)
      REQUIREMENTS_PATH="${2:-}"
      shift 2
      ;;
    --skip-create-database)
      SKIP_CREATE_DATABASE=1
      shift
      ;;
    --force-recreate-venv)
      FORCE_RECREATE_VENV=1
      shift
      *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "init-env" && "$MODE" != "provision" ]]; then
  echo "--mode must be init-env or provision." >&2
  exit 1
fi

PYTHON_CMD="$(resolve_python)"
if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python is not installed or not on PATH." >&2
  exit 1
fi

# Resolve requirements path relative to project root when relative
REQ_CANDIDATE="$REQUIREMENTS_PATH"
if [[ "$REQ_CANDIDATE" != /* ]]; then
  REQ_CANDIDATE="$PROJECT_ROOT/${REQ_CANDIDATE#./}"
fi

if [[ "$MODE" == "init-env" ]]; then
  echo ""
  echo "== LA-Server production setup ($MODE) =="
  require_python_314 "$PYTHON_CMD"

  if [[ ! -f "$ENV_PATH" ]]; then
    if [[ ! -f "$ENV_EXAMPLE_PATH" ]]; then
      echo "Missing '$ENV_EXAMPLE_PATH' (needed to create '.env')." >&2
      exit 1
    fi
    cp "$ENV_EXAMPLE_PATH" "$ENV_PATH"
    echo "Created '$ENV_PATH' from '.env.example'."
  else
    echo ".env already exists at: $ENV_PATH"
  fi

  echo ""
  echo "Update '.env' now with production values (DEBUG=false, SECRET_KEY, MariaDB settings)."
  echo "Then run: ./scripts/setup.sh --mode provision"
  echo ""
  exit 0
fi

# provision
echo ""
echo "== LA-Server production setup ($MODE) =="
require_python_314 "$PYTHON_CMD"

if [[ ! -f "$ENV_PATH" ]]; then
  echo ".env does not exist. Run './scripts/setup.sh --mode init-env' first." >&2
  exit 1
fi

if ! env_is_customized "$ENV_PATH" "$ENV_EXAMPLE_PATH"; then
  echo ".env appears unchanged or still contains placeholder values. Please update it before running provision mode." >&2
  exit 1
fi

if [[ "$FORCE_RECREATE_VENV" -eq 1 && -d "$VENV_PATH" ]]; then
  echo "Recreating virtual environment at '$VENV_PATH'..."
  rm -rf "$VENV_PATH"
fi

if [[ ! -d "$VENV_PATH" ]]; then
  echo "Creating virtual environment at '$VENV_PATH'..."
  "$PYTHON_CMD" -m venv "$VENV_PATH"
fi

# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"

echo ""
echo "Upgrading pip..."
python -m pip install --upgrade pip

RESOLVED_REQ="$(resolve_requirements_file "$REQ_CANDIDATE" "$REPO_REQUIREMENTS_PATH")"
echo ""
echo "Installing dependencies from '$RESOLVED_REQ'..."
python -m pip install -r "$RESOLVED_REQ"

if [[ "$SKIP_CREATE_DATABASE" -eq 0 ]]; then
  echo ""
  echo "Creating production database (scripts/create_database.py)..."
  python "$PROJECT_ROOT/scripts/create_database.py"
fi

echo ""
echo "Setup complete."
echo ""
echo "Run: ./start.sh to start the LA-Server"
echo ""

exit 0
