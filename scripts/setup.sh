#!/usr/bin/env bash
# LA-Server setup: production (no Poetry) or development (Poetry). Same behavior as scripts/setup.ps1.
#
# Usage:
#   ./scripts/setup.sh [--mode init-env|provision|development|help] [--requirements-path PATH]
#                        [--skip-create-database] [--force-recreate-venv]
#                        [--skip-test-env-check] [--force-recreate-poetry-venv]
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
SKIP_TEST_ENV_CHECK=0
FORCE_RECREATE_POETRY_VENV=0

usage() {
  cat <<EOF
LA-Server setup (same behavior as scripts/setup.ps1).

Production (no Poetry): data/requirements.txt is a poetry export; edit pyproject.toml first, then re-export.
- init-env: create .env from .env.example (if missing) and stop.
- provision: verify .env was customized, create .venv, pip install -r, create database.

Development (Poetry: poetry install --with dev, pre-commit, optional checks):
- development: poetry self add poetry-plugin-export, poetry install --with dev, pre-commit install, optional pytest/MariaDB checks.
- help: show this help (same as -h, --help).

Options:
  --mode <init-env|provision|development|help>  Default: init-env.
  --requirements-path <path>    requirements file for provision (default: ./data/requirements.txt from project root).
  --skip-create-database        Do not run scripts/create_database.py in provision mode.
  --force-recreate-venv         Remove .venv and recreate it before pip install in provision mode.
  --skip-test-env-check         Skip pytest --collect-only and MariaDB check in development mode.
  --force-recreate-poetry-venv  Remove .venv and Poetry envs for this project, then development install.
  -h, --help                    Show this help.

Examples:
  ./scripts/setup.sh --mode init-env
  ./scripts/setup.sh --mode provision
  ./scripts/setup.sh --mode development
  ./scripts/setup.sh --mode development --skip-test-env-check
  ./scripts/setup.sh --mode development --force-recreate-poetry-venv
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

require_poetry() {
  if ! command -v poetry >/dev/null 2>&1; then
    echo "Poetry is not on PATH. Install: https://python-poetry.org/docs/#installation" >&2
    exit 1
  fi
}

resolve_requirements_file() {
  local py_cmd="$1"
  local candidate="$2"
  local fallback="$3"
  if [[ -f "$candidate" ]]; then
    "$py_cmd" -c "import os, sys; print(os.path.abspath(sys.argv[1]))" "$candidate"
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
      ;;
    --skip-test-env-check)
      SKIP_TEST_ENV_CHECK=1
      shift
      ;;
    --force-recreate-poetry-venv)
      FORCE_RECREATE_POETRY_VENV=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$MODE" == "help" ]]; then
  usage
  exit 0
fi

if [[ "$MODE" != "init-env" && "$MODE" != "provision" && "$MODE" != "development" ]]; then
  echo "--mode must be init-env, provision, development, or help." >&2
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

# ------------------------------------------------------------------------ init-env
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
  echo "Then run: ./scripts/setup.sh --mode provision   (or --mode development for Poetry)"
  echo ""
  exit 0
fi

# ------------------------------------------------------------------------ provision
if [[ "$MODE" == "provision" ]]; then
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

  RESOLVED_REQ="$(resolve_requirements_file "python" "$REQ_CANDIDATE" "$REPO_REQUIREMENTS_PATH")"
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
fi

# ------------------------------------------------------------------------ development
echo ""
echo "== LA-Server development setup (development) =="
echo ""

require_python_314 "$PYTHON_CMD"
require_poetry

cd "$PROJECT_ROOT"

if [[ "$FORCE_RECREATE_POETRY_VENV" -eq 1 ]]; then
  echo "Removing in-project .venv and Poetry virtualenvs for this project (force-recreate-poetry-venv)..." >&2
  if [[ -d "$VENV_PATH" ]]; then
    rm -rf "$VENV_PATH"
  fi
  poetry env remove --all 2>/dev/null || true
  echo ""
fi

echo "Configuring in-project virtualenv (poetry.toml)..."
poetry config virtualenvs.in-project true --local

export POETRY_NO_INTERACTION=1
echo "Installing Poetry export plugin (poetry-plugin-export)..."
poetry self add poetry-plugin-export
echo ""

if [[ ! -f "$ENV_PATH" ]]; then
  if [[ ! -f "$ENV_EXAMPLE_PATH" ]]; then
    echo "Missing '$ENV_EXAMPLE_PATH' (cannot create .env)." >&2
    exit 1
  fi
  cp "$ENV_EXAMPLE_PATH" "$ENV_PATH"
  echo "Created '$ENV_PATH' from '.env.example'."
  echo "Set SECRET_KEY and MariaDB values in '.env' before running the app or tests (see README, .env.example)."
  echo ""
else
  echo "Using existing .env at: $ENV_PATH"
  echo ""
fi

echo "Installing dependencies (poetry install --with dev)..."
poetry install --with dev

echo ""
echo "Installing Git pre-commit hooks (poetry run pre-commit install)..."
poetry run pre-commit install

if [[ "$SKIP_TEST_ENV_CHECK" -eq 1 ]]; then
  echo ""
  echo "Skipped test environment checks (--skip-test-env-check)." >&2
else
  echo ""
  echo "Validating test discovery (pytest --collect-only)..."
  poetry run pytest --collect-only -q

  echo ""
  echo "Validating MariaDB (admin connection from .env)..."
  MARIADB_ONELINER='import os, sys; sys.path.insert(0, os.getcwd()); from sqlalchemy import create_engine, text; from sqlalchemy.pool import NullPool; from app.config import Config; e = create_engine(Config.admin_db_uri(), poolclass=NullPool, connect_args={"connect_timeout": 10}); c = e.connect(); c.execute(text("SELECT 1")); c.close(); print("MariaDB: connection OK")'
  if ! poetry run python -c "$MARIADB_ONELINER"; then
    echo "Ensure MariaDB is running and .env has correct MARIADB_HOST, MARIADB_PORT, MARIADB_USER, MARIADB_PASSWORD (see README)." >&2
    exit 1
  fi
fi

echo ""
echo "Development setup complete."
echo "Use: poetry run pytest | poetry run pre-commit run --all-files | ./start.sh"
echo ""

exit 0
