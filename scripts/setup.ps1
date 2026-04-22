<#
.SYNOPSIS
Sets up the LA-Server for the Kinderspielstadt Los Ämmerles: production (venv + requirements) or
development (Poetry, dev tools, pre-commit, test checks).

.DESCRIPTION
Production (no Poetry): `pip install -r` uses `data/requirements.txt` (a `poetry export` of `pyproject.toml` / `poetry.lock` — not where you add deps; edit `pyproject.toml` first, then re-export).
- `init-env`: Create `.env` from `.env.example` (if missing) and stop.
- `provision`: Verify `.env` was customized, create `.venv`, `pip install -r`, create database.

Development (use Poetry only: `poetry` + `pyproject.toml` / lockfile, same as CI `poetry install --with dev`):
- `development`: `poetry self add poetry-plugin-export` (enables `poetry export` for `data/requirements.txt`), `poetry install --with dev`, `pre-commit install`, optional test/MariaDB validation.

.PARAMETER Mode
Invocation mode: `init-env` (default), `provision`, `development`, or `help` (same as `-Help`).

.PARAMETER RequirementsPath
Where to find the production `requirements.txt`.
Default: `./data/requirements.txt`.

.PARAMETER SkipCreateDatabase
If set, skips running `scripts/create_database.py` (production `provision` only).

.PARAMETER ForceRecreateVenv
If set, deletes `./.venv` and recreates it (production `provision` only).

.PARAMETER SkipTestEnvCheck
If set, skips `pytest --collect-only` and MariaDB connectivity (`-Mode development` only).

.PARAMETER ForceRecreatePoetryVenv
If set, removes `./.venv` and all Poetry virtualenvs for this project, then installs again (`-Mode development` only). Use when switching from `provision` (pip) to Poetry, or if Poetry reports a broken venv and imports fail (e.g. `No module named 'sqlalchemy'`).

.EXAMPLE
./scripts/setup.ps1 -Mode init-env

.EXAMPLE
./scripts/setup.ps1 -Mode provision

.EXAMPLE
./scripts/setup.ps1 -Mode development

.EXAMPLE
./scripts/setup.ps1 -Mode development -SkipTestEnvCheck

.EXAMPLE
./scripts/setup.ps1 -Mode development -ForceRecreatePoetryVenv

.EXAMPLE
./scripts/setup.ps1 -Mode provision -ForceRecreateVenv -RequirementsPath "./data/requirements.txt"
#>


param(
    # Help-Switch mit Alias -h
    [Alias("h")]
    [switch]$Help,

    [ValidateSet("init-env", "provision", "development", "help")]
    [string]$Mode = "init-env",
    [string]$RequirementsPath = "./data/requirements.txt",
    [switch]$SkipCreateDatabase,
    [switch]$ForceRecreateVenv,
    [switch]$SkipTestEnvCheck,
    [switch]$ForceRecreatePoetryVenv
)

$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $PSScriptRoot "setup.ps1"
if ($Help -or $Mode -eq "help") {
    # Use positional script path (not -Path); -Path targets a different help feature in some hosts.
    Get-Help $ScriptPath -Full
    exit 0
}

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPath = Join-Path $ProjectRoot ".venv"
$EnvExamplePath = Join-Path $ProjectRoot ".env.example"
$EnvPath = Join-Path $ProjectRoot ".env"
$RepoRequirementsPath = Join-Path $ProjectRoot "data/requirements.txt"

$PythonVersion = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        $PythonRawVersion = (python --version 2>&1 | Out-String).Trim()
        $PythonVersionString = $PythonRawVersion -replace "Python\s*", ""
        $PythonVersion = [version]($PythonVersionString.Trim())
    } catch {
        $PythonVersion = $null
    }
}

function Resolve-RequirementsFile {
    param([string]$CandidatePath, [string]$FallbackPath)

    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    if ($CandidatePath -and -not [System.IO.Path]::IsPathRooted($CandidatePath)) {
        $rel = ($CandidatePath -replace '^\.[/\\]', "").Replace("/", [char][System.IO.Path]::DirectorySeparatorChar)
        $CandidatePath = Join-Path $projectRoot $rel
    }

    if (Test-Path $CandidatePath) {
        return (Resolve-Path $CandidatePath)
    }
    if (Test-Path $FallbackPath) {
        Write-Host "Requirements not found at '$CandidatePath'. Falling back to '$FallbackPath'."
        return (Resolve-Path $FallbackPath)
    }

    Write-Host "Requirements file not found. Checked '$CandidatePath' and '$FallbackPath'." -ForegroundColor Red
    exit 1
}

function Test-EnvCustomized {
    param([string]$EnvFilePath, [string]$EnvExampleFilePath)

    if (-not (Test-Path $EnvFilePath)) {
        return $false
    }

    if (-not (Test-Path $EnvExampleFilePath)) {
        return $true
    }

    $envContent = Get-Content -Raw -Path $EnvFilePath
    $exampleContent = Get-Content -Raw -Path $EnvExampleFilePath

    if ($envContent -eq $exampleContent) {
        return $false
    }

    # Basic placeholder guard to catch common "not configured yet" cases.
    $stillUsingPlaceholders = (
        $envContent -notmatch "SECRET_KEY=your-secret-key-here" -or
        $envContent -notmatch "MARIADB_PASSWORD=your-password"
    )

    return $stillUsingPlaceholders
}

# ------------------------------------------------------------------------
# Mode - init-env (default)
# ------------------------------------------------------------------------
if ($Mode -eq "init-env") {
    Write-Host ""
    Write-Host "== LA-Server production setup ($Mode) =="

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Python is not installed" -ForegroundColor Red
        exit 1
    }

    if ($null -eq $PythonVersion -or $PythonVersion -lt [version]"3.14.0") {
        Write-Host "Python 3.14 or higher is required. Found Python version: $PythonVersion" -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Path $EnvPath)) {
        if (-not (Test-Path $EnvExamplePath)) {
            Write-Host "Missing '$EnvExamplePath' (needed to create '.env')."
        }
        Copy-Item $EnvExamplePath $EnvPath
        Write-Host "Created '$EnvPath' from '.env.example'."

    } else {
        Write-Host "'.env' already exists at: '$EnvPath'"
    }

    Write-Host ""
    Write-Host "Update '.env' now with production values (DEBUG=false, SECRET_KEY, MariaDB settings)." -ForegroundColor Green
    Write-Host "'Then run: ./scripts/setup.ps1 -Mode provision'" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# ------------------------------------------------------------------------
# Mode - provision
# ------------------------------------------------------------------------
elseif ($Mode -eq "provision") {
    Write-Host ""
    Write-Host "== LA-Server production setup ($Mode) =="

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Python is not installed" -ForegroundColor Red
        exit 1
    }

    if ($null -eq $PythonVersion -or $PythonVersion -lt [version]"3.14.0") {
        Write-Host "Python 3.14 or higher is required. Found Python version: $PythonVersion" -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Path $EnvPath)) {
        Write-Host "'.env' does not exist. Run './scripts/setup.ps1 -Mode init-env' first." -ForegroundColor Red
        exit 1
    }

    if (-not (Test-EnvCustomized -EnvFilePath $EnvPath -EnvExampleFilePath $EnvExamplePath)) {
        Write-Host "'.env' appears unchanged or still contains placeholder values. Please update it before running provision mode." -ForegroundColor Red
        exit 1
    }

    # 1. Create virtual environment
    if ($ForceRecreateVenv -and (Test-Path $VenvPath)) {
        Write-Host "Recreating virtual environment at '$VenvPath'..." -ForegroundColor Green
        Remove-Item -Recurse -Force $VenvPath
    }

    if (-not (Test-Path $VenvPath)) {
        Write-Host "Creating virtual environment at '$VenvPath'..." -ForegroundColor Green
        & python -m venv $VenvPath
    }

    # 2. Activate venv and install dependencies
    $ActivatePath = Join-Path $VenvPath "Scripts/Activate.ps1"
    if (-not (Test-Path $ActivatePath)) {
        Write-Host "Could not find venv activation script at '$ActivatePath'." -ForegroundColor Red
        exit 1
    }

    . $ActivatePath

    Write-Host ""
    Write-Host "Upgrading pip..." -ForegroundColor Green
    python -m pip install --upgrade pip

    $ResolvedRequirements = Resolve-RequirementsFile -CandidatePath $RequirementsPath -FallbackPath $RepoRequirementsPath
    Write-Host ""
    Write-Host "Installing dependencies from '$ResolvedRequirements'..." -ForegroundColor Green
    python -m pip install -r $ResolvedRequirements

    # 3. Create database
    if (-not $SkipCreateDatabase) {
        Write-Host ""
        Write-Host "Creating production database (scripts/create_database.py)..." -ForegroundColor Green
        & python (Join-Path $ProjectRoot "scripts/create_database.py")
    }

    Write-Host ""
    Write-Host "Setup complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "Run: '.\start.ps1' to start the LA-Server" -ForegroundColor Green
    Write-Host ""

    exit 0
}


# ------------------------------------------------------------------------
# Mode - development
# ------------------------------------------------------------------------
elseif ($Mode -eq "development") {
    Write-Host ""
    Write-Host "== LA-Server development setup ($Mode) =="
    Write-Host ""

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Python is not installed" -ForegroundColor Red
        exit 1
    }

    if ($null -eq $PythonVersion -or $PythonVersion -lt [version]"3.14.0") {
        Write-Host "Python 3.14 or higher is required. Found Python version: $PythonVersion" -ForegroundColor Red
        exit 1
    }

    if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
        Write-Host "Poetry is not on PATH. Install: https://python-poetry.org/docs/#installation" -ForegroundColor Red
        exit 1
    }

    $rootPath = $ProjectRoot.Path
    Push-Location -LiteralPath $rootPath
    try {
        if ($ForceRecreatePoetryVenv) {
            Write-Host "Removing in-project .venv and Poetry virtualenvs for this project (ForceRecreatePoetryVenv)..." -ForegroundColor Yellow
            if (Test-Path -LiteralPath $VenvPath) {
                Remove-Item -Recurse -Force -LiteralPath $VenvPath
            }
            & poetry env remove --all 2>$null
            Write-Host ""
        }

        # Poetry in-project venv: ./.venv (see poetry.toml) — the development environment, not pip/provision.
        & poetry config virtualenvs.in-project true --local
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        Write-Host 'Installing Poetry export plugin (poetry-plugin-export) so poetry export works for data/requirements.txt...' -ForegroundColor Green
        $env:POETRY_NO_INTERACTION = "1"
        & poetry self add poetry-plugin-export
        Remove-Item Env:POETRY_NO_INTERACTION -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host ""

        if (-not (Test-Path -LiteralPath $EnvPath)) {
            if (-not (Test-Path -LiteralPath $EnvExamplePath)) {
                Write-Host "Missing '$EnvExamplePath' (cannot create .env)." -ForegroundColor Red
                exit 1
            }
            Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
            Write-Host "Created '$EnvPath' from '.env.example'." -ForegroundColor Green
            Write-Host "Set SECRET_KEY and MariaDB values in '.env' before running the app or tests (see README, .env.example)." -ForegroundColor Yellow
            Write-Host ""
        } else {
            Write-Host "Using existing .env at: $EnvPath"
            Write-Host ""
        }

        Write-Host "Installing dependencies (poetry install --with dev)..." -ForegroundColor Green
        & poetry install --with dev
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        Write-Host ""
        Write-Host "Installing Git pre-commit hooks (poetry run pre-commit install)..." -ForegroundColor Green
        & poetry run pre-commit install
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        if ($SkipTestEnvCheck) {
            Write-Host ""
            Write-Host "Skipped test environment checks (-SkipTestEnvCheck)." -ForegroundColor Yellow
        } else {
            Write-Host ""
            Write-Host "Validating test discovery (pytest --collect-only)..." -ForegroundColor Green
            & poetry run pytest --collect-only -q
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

            Write-Host ""
            Write-Host "Validating MariaDB (admin connection from .env)..." -ForegroundColor Green
            $mariadbOneLiner = 'import os, sys; sys.path.insert(0, os.getcwd()); from sqlalchemy import create_engine, text; from sqlalchemy.pool import NullPool; from app.config import Config; e = create_engine(Config.admin_db_uri(), poolclass=NullPool, connect_args={''connect_timeout'': 10}); c = e.connect(); c.execute(text(''SELECT 1'')); c.close(); print(''MariaDB: connection OK'')'
            & poetry run python -c $mariadbOneLiner
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Ensure MariaDB is running and .env has correct MARIADB_HOST, MARIADB_PORT, MARIADB_USER, MARIADB_PASSWORD (see README)." -ForegroundColor Yellow
                exit 1
            }
        }
    } finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "Development setup complete." -ForegroundColor Green
    Write-Host "Use: poetry run pytest | poetry run pre-commit run --all-files | .\\start.ps1" -ForegroundColor Green
    Write-Host ""
    exit 0
}

else {
    Write-Host "Unknown mode: $Mode" -ForegroundColor Red
    exit 1
}
