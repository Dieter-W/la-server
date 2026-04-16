<#
.SYNOPSIS
Sets up the production LA-Server for the Kinderspielstadt Los Ämmerles in two steps.

This production installation is intended for environments where Poetry is NOT used.
Dependencies are installed from `/data/requirements.txt`.

.DESCRIPTION
Two invocation modes:
1) `init-env`: Create `.env` from `.env.example` (if missing) and stop.
2) `provision`: Verify `.env` exists and was updated by the user, then create
   `.venv`, install dependencies from requirements, and create the database.

.PARAMETER Mode
Invocation mode. Allowed values:
- `init-env` (default): only prepare `.env` and stop.
- `provision`: run full setup after `.env` has been customized.

.PARAMETER RequirementsPath
Where to find the production `requirements.txt`.
Default: `/data/requirements.txt`.

.PARAMETER SkipCreateDatabase
If set, skips running `scripts/create_database.py`.

.PARAMETER ForceRecreateVenv
If set, deletes `./.venv` and recreates it.

.EXAMPLE
./scripts/$Setup.ps1 -Mode init-env

.EXAMPLE
./scripts/$Setup.ps1 -Mode provision

.EXAMPLE
./scripts/$Setup.ps1 -Mode provision -ForceRecreateVenv -RequirementsPath "/data/requirements.txt"
#>


param(
    # Help-Switch mit Alias -h
    [Alias("h")]
    [switch]$Help,

    [ValidateSet("init-env", "provision")]
    [string]$Mode = "init-env",
    [string]$RequirementsPath = "./data/requirements.txt",
    [switch]$SkipCreateDatabase,
    [switch]$ForceRecreateVenv
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPath = Join-Path $ProjectRoot ".venv"
$EnvExamplePath = Join-Path $ProjectRoot ".env.example"
$EnvPath = Join-Path $ProjectRoot ".env"
$RepoRequirementsPath = Join-Path $ProjectRoot "data/requirements.txt"

$PythonRawVersion = python --version 2>&1
$PythonVersionString = $PythonRawVersion -replace "Python", ""
$PythonVersion = [version]$PythonVersionString

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

    if ($PythonVersion -lt [version]"3.14.0") {
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
    Write-Host "'Then run: ./scripts/$Setup.ps1 -Mode provision'" -ForegroundColor Green
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

    if ($PythonVersion -lt [version]"3.14.0") {
        Write-Host "Python 3.14 or higher is required. Found Python version: $PythonVersion" -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Path $EnvPath)) {
        Write-Host "'.env' does not exist. Run './scripts/$Setup.ps1 -Mode init-env' first." -ForegroundColor Red
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
# Help-Logik: When -h or -Help is used
# ------------------------------------------------------------------------
elseif ($Help) {
    Get-Help $PSCommandPath -Full
    exit 0
}
else {
    Get-Help $PSCommandPath -Full
    exit 0
}
