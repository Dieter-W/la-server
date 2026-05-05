# Kinderspielstadt Los Ämmerles - LA-Server

This project supports the [Kinderspielstadt](https://de.wikipedia.org/wiki/Kinderstadt) in Ammerbuch ([Los Ämmerles](https://los-aemmerles.de/)) to digitalize the summer camp.  Together with the connected clients (la-job-center, la-job-center-kiosk-mode, …), **children and staff** (camp participants in the Spielstadt) use the system during the camp.

The server is a Python Flask server with MariaDB database backend.  The production implementation with [waitress](https://github.com/Pylons/waitress) runs with 4 threads.


## Prerequisites

The **"Kinderspielstadt Los Ämmerles - LA-Server"** requires Python, installed on your local computer.  MariaDB can be installed locally or you can connect to a database installed on the internet.

The following versions are required to run the LA-Server:

- Python 3.14+
- MariaDB 10.6+

## Authorization

In client apps users sign in with **employee number** and **password**. The server returns a short-lived **access** JWT (`token`) sent as **`Authorization: Bearer`** on ordinary API calls, plus a separate **refresh** JWT (`refresh_token`) that is sent the same way only to **`POST /api/auth/refresh`** to obtain a new access JWT. Exact headers and error handling: [docs/developer-guide.md](./docs/developer-guide.md).

Some operations are open to everyone (public). Others need a signed-in user; a few need **staff** or **admin**, the most need **employee** (all kids in the summer camp). The **API Endpoints** table below marks each route as **public** or with the minimum type of account that is allowed.

### Initial password

When an account is **created** (`POST /api/employees`), **imported from CSV** ([CSV bulk import](#csv-bulk-import)), or when **staff or admin runs a password reset** (`POST /api/auth/password/reset-password`), the server sets the login secret from the participant’s **`last_name`** (trimmed, then hashed). **Sign-in treats the password as case-insensitive**, so the surname can be typed in normal spelling. The account stays flagged **`password_must_change`** until the user picks their own password with **`POST /api/auth/password/set-password`**. The **login** response includes that flag so client apps can send new users through “change password” immediately after the first sign-in.

## Setup (Production, no Poetry)

1. **Clone or copy the GIT repository**

   The public repository URL is not published yet; use your team’s clone URL or a downloaded archive when available.

   Usually the copy is done with the git command: `git clone https://github.com/Dieter-W/la-server.git`.  You can also download a zip or tarball from [GitHub](https://github.com/Dieter-W/la-Server) to create the LA-Server directory.

2. **Initialize `.env` and `village_data/`**

   **`init-env`** (both scripts) creates `.env` from `.env.example` when it is missing. If `village_data/` is also missing, the script creates it and seeds it from the repo’s `data/` tree: it **requires** `data/village.ini`; it copies `data/images/logo.jpg` when present (and warns if not); it copies `data/images/favicon.png` only when that file exists (otherwise add `village_data/images/favicon.png` yourself). When `data/csv-example/employees_sample.csv` and `data/csv-example/companies_sample.csv` exist, **init-env** copies each into `village_data/` **only if that filename is not already there** (so existing camp copies are not overwritten), whether `village_data/` was just created or already existed (and warns if a source file is missing). See the **Village data** section below.

   Windows (PowerShell):

   ```powershell
   .\scripts\setup.ps1 -Mode init-env
   ```

   Linux / macOS / Git Bash (make the script executable once: `chmod +x './scripts/setup.sh'`):

   ```bash
   './scripts/setup.sh' --mode init-env
   ```

3. **Update `.env`**

   Set production values (at minimum `DEBUG=false`, `SECRET_KEY`, and MariaDB credentials).

4. **Provision environment**

   Windows (PowerShell):

   ```powershell
   .\scripts\setup.ps1 -Mode provision
   ```

   Linux / macOS / Git Bash:

   ```bash
   './scripts/setup.sh' --mode provision
   ```

   This checks that `.env` was customized, then creates or reuses `.venv`, installs dependencies from `data/requirements.txt`, and runs `scripts/create_database.py` unless you skip that step (see parameters below).

**Manual alternative (same as `provision` without the scripts):**

```bash
python3 -m venv .venv
source .venv/bin/activate   # Git Bash on Windows: source .venv/Scripts/activate
pip install -r data/requirements.txt
python ./scripts/create_database.py
```

### `setup.ps1` parameters (Windows)

The options below are for **production** setup only (`-Mode init-env` or `provision`). For other script modes, see [docs/developer-guide.md](docs/developer-guide.md).

- `-Mode <init-env|provision>`: `init-env` creates `.env` (if missing), bootstraps `village_data/` from `data/` when that folder is absent (see step 2 above), then exits; `provision` runs full production setup (venv, `pip install -r`, database creation).
- `-RequirementsPath <string>`: Path to the production `requirements.txt` (`provision` only). Default: `.\data\requirements.txt`.
- `-SkipCreateDatabase`: Skip running `python .\scripts\create_database.py` (`provision` only).
- `-ForceRecreateVenv`: Delete `.\.venv` if it exists and recreate it before installing dependencies (`provision` only).

```powershell
.\scripts\setup.ps1 -Mode init-env
.\scripts\setup.ps1 -Mode provision
.\scripts\setup.ps1 -Mode provision -SkipCreateDatabase
.\scripts\setup.ps1 -Mode provision -ForceRecreateVenv -RequirementsPath ".\data\requirements.txt"
```

### `setup.sh` parameters (Linux / macOS / Git Bash)

The options below are for **production** setup only (`--mode init-env` or `provision`). For other script modes, see [docs/developer-guide.md](docs/developer-guide.md).

- `--mode <init-env|provision>`: `init-env` creates `.env` (if missing), bootstraps `village_data/` from `data/` when that folder is absent (see step 2), then exits; `provision` runs full production setup (same as PowerShell).
- `--requirements-path <path>`: Path to the production `requirements.txt` (`provision` only). Default: `./data/requirements.txt` (relative to the project root).
- `--skip-create-database`: Skip `python ./scripts/create_database.py` (`provision` only).
- `--force-recreate-venv`: Remove `./.venv` and recreate it before installing dependencies (`provision` only).
- `-h` / `--help`: Show script usage and all supported modes.

```bash
'./scripts/setup.sh' --mode init-env
'./scripts/setup.sh' --mode provision
'./scripts/setup.sh' --mode provision --skip-create-database
'./scripts/setup.sh' --mode provision --force-recreate-venv --requirements-path ./data/requirements.txt
```

## Village data (`village_data/`)

Before you **run LA-Server**, the camp-specific configuration and branding files must be present in the `village_data/` directory at the **project root** (alongside `main.py`). The repository includes a sample `village_data/` tree you can edit per deployment. Canonical bulk-import examples live under **`data/csv-example/`** in the repo; **`init-env`** copies those CSVs into `village_data/` when the matching filename is not already present there (see setup step 2). If you start from a layout **without** `village_data/`, run **`init-env`** once (`.\scripts\setup.ps1 -Mode init-env` or `./scripts/setup.sh --mode init-env`): it recreates that folder from `data/` as described in setup step 2. The API exposes INI and image paths to clients (e.g. job center apps) so each Spielstadt can show the correct name, currency, and imagery without changing code. Sample CSVs in `village_data/` are only for operators running bulk import; they are not served by the HTTP API.

| Path | Role |
| ---- | ---- |
| `village_data/village.ini` | INI file with sections below; read on each request (with caching by file modification time). |
| `village_data/images/` | Binary assets referenced from `village.ini` (paths are **relative to `village_data/`**). |
| `village_data/employees_sample.csv` | Optional template for [CSV bulk import](#csv-bulk-import); filled from `data/csv-example/` by **init-env** when missing in `village_data/`. |
| `village_data/companies_sample.csv` | Optional template for companies bulk import; same as above. |

### `village.ini` sections

- **`[general]`** — Display context for the Spielstadt: e.g. `name`, `location`, `language`, `year`.
- **`[currency]`** — In-game money label: e.g. `name`, `name_short` (values may be quoted in the INI; the server strips optional double quotes).
- **`[village-images]`** — Filenames relative to `village_data/`, for example `logo = images/logo.jpg` and `favicon = images/favicon.png`. Missing files or bad paths result in HTTP 404 from the image endpoints.

Further API detail: [docs/developer-guide.md](./docs/developer-guide.md).

## Run LA-Server

**Option 1 – Start scripts** (activate venv automatically):

```bash
.\start.ps1      # Windows PowerShell
./start.sh       # Linux/macOS (chmod +x start.sh first)
```

**Option 2 – Manual:**

```bash
python main.py
```

The LA-Server starts at `http://localhost:5000`.

- **Development** (`DEBUG=true`): Flask built-in server with auto-reload.
- **Production** (`DEBUG=false`): Waitress WSGI server with 4 worker threads.

## Production

For production deployment, ensure the following:

### Required

1. **Set `DEBUG=false`** in `.env`
  Uses the Waitress WSGI server instead of the Flask dev server.
2. **Set a strong `SECRET_KEY`**
  Generate a random key (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`) and set it in `.env`. Never commit production secrets.
3. **Configure production database**
  Set `MARIADB_HOST`, `MARIADB_PORT` (if not the default `3306`), `MARIADB_USER`, `MARIADB_PASSWORD`, and `MARIADB_DATABASE` for your production MariaDB instance.

### Optional environment variables


| Variable             | Default   | Description                                                                                                                           |
| -------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `HOST`               | `0.0.0.0` | Bind address                                                                                                                          |
| `PORT`               | `5000`    | Listen port                                                                                                                           |
| `THREADS`            | `4`       | Number of Waitress worker threads. With `DEBUG=true`, use `THREADS=0` to run Flask’s dev server single-threaded (see `.env.example`). |
| `MARIADB_PORT`       | `3306`    | MariaDB TCP port                                                                                                                      |
| `VALIDATE_CHECK_SUM` | `true`    | When `true`, employee numbers must pass the ISO 7064 Mod 97,10 checksum (API and bulk import).                                        |


### Direct Waitress start

```bash
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 main:app
```



## CSV bulk import

### Import companies from a CSV file:

```bash
python ./scripts/bulk_import_companies.py companies.csv
```

Example inputs: `village_data/companies_sample.csv`has created. You can use `village_data/companies_sample.csv` as a template for your own file and bulk-import into the database. The same sample also lives under `data/csv-example/companies_sample.csv`.

**CSV format:** Comma-separated with a header row. Required columns: `company_name`, `jobs_max`, `hourly_pay`, `active`, `notes`.

Templates ship in **`data/csv-example/companies_sample.csv`** (and **init-env** places a copy in `village_data/` when that file is not already there). Example excerpt:

```csv
company_name,jobs_max,hourly_pay,active,notes
Bank,8,10,true,,
Arbeitsamt,7,10,true,
Bauhof,8,10,true,
Küche,10,15,false,Only weekdays
```

The script creates or updates companies (by `company_name`) and logs successes and errors to stdout. It exits with a non-zero code if any row fails to import.

### Import employees from a CSV file:

```bash
python ./scripts/bulk_import_employees.py employees.csv
```

Example inputs: `village_data/employees_sample.csv` has created. You can use `village_data/employees_sample.csv` as a template for your own file and bulk-import everyone into the database. The same sample also lives under `data/csv-example/employees_sample.csv`.

The script takes **only** the path to the CSV file. Employee-number checksum validation follows **`VALIDATE_CHECK_SUM`** in `.env` (default `true`; see Optional environment variables above). To disable validation for local testing only, set `VALIDATE_CHECK_SUM=false` in `.env`.

**Note:**
It's useful to use employee numbers with checksums, otherwise a typo can refer to a different camp participant. A full explanation of how to create employee numbers with checksums in Excel is in `[./docs/employee-numbers.md](./docs/employee-numbers.md)`.

**CSV format:** Comma-separated with a header row. Required columns: `first_name`, `last_name`, `employee_number`, `role`, `active`, `auth_group`, `notes`. Empty rows are skipped (including a trailing spreadsheet row).

`auth_group` must be one of `employee`, `staff`, or `admin`.

Templates ship in **`data/csv-example/employees_sample.csv`** (and **init-env** places a copy in `village_data/` when that file is not already there). Example excerpt:

```csv
first_name,last_name,employee_number,role,active,auth_group,notes
Max,Mustermann,M00155,Kind,false,Employee,Works weekends
Monika,Mustermann,M00252,Kind,true,Employee,
Anna,Schmidt,A00265,Helferin,true,Staff,
Peter,Krause,P00370,Leiter,true,Admin,Team lead
```

The script creates or updates camp participants one row per `employee_number`—and logs successes and errors to stdout. It exits with a non-zero code if any row fails to import.


## API Endpoints

In the table, **Authorization** is shorthand for:

- **public** — no sign-in needed.
- **employee or higher** — signed in as a camp participant (any normal login).
- **staff or higher** — signed in as staff or admin.
- **admin required** — signed in as an admin.

If an admin changes another person’s access (`POST /api/auth/set-auth-group`), that person should **sign in again** so the app remembers the new permissions.

| Method | Path                                     | Summary                                     | Authorization                    |
| ------ | ---------------------------------------- | ------------------------------------------- | -------------------------------- |
| GET    | `/api/health`                            | Liveness                                    | public                           |
| GET    | `/api/health/db`                         | Database connectivity                       | public                           |
| GET    | `/api/health/runtime`                    | Pool, peaks, redacted DB (no customer data) | admin required                   |
| POST   | `/api/auth/login`                        | Sign in                                     | public                           |
| POST   | `/api/auth/set-auth-group`               | Change another user’s permission level      | admin required                   |
| GET    | `/api/auth/me`                           | Current employee profile                    | employee or higher               |
| POST   | `/api/auth/password/set-password`        | Change password                             | employee or higher               |
| POST   | `/api/auth/password/reset-password`      | Reset password to initial value             | staff or higher                  |
| POST   | `/api/auth/refresh`                      | New access token                            | employee or higher               |
| POST   | `/api/auth/logout`                       | Logout                                      | employee or higher               |
| GET    | `/api/companies`                         | List companies                              | public                           |
| GET    | `/api/companies/<company_name>`          | List one company                            | public                           |
| POST   | `/api/companies`                         | Create company                              | admin required                   |
| PUT    | `/api/companies/<company_name>`          | Update company                              | admin required                   |
| DELETE | `/api/companies/<company_name>`          | Delete company                              | admin required                   |
| GET    | `/api/employees`                         | List employees                              | public                           |
| GET    | `/api/employees/<employee_number>`       | List one employee                           | public                           |
| POST   | `/api/employees`                         | Create employee                             | admin required                   |
| PUT    | `/api/employees/<employee_number>`       | Update employee                             | admin required                   |
| DELETE | `/api/employees/<employee_number>`       | Soft or hard delete employee                | admin required                   |
| GET    | `/api/job-assignments`                   | List job assignments                        | public                           |
| POST   | `/api/job-assignments`                   | Create job assignment                       | employee or higher               |
| DELETE | `/api/job-assignments/<employee_number>` | Remove assignment for employee              | employee or higher               |
| POST   | `/api/job-assignments/reset`             | Reset assignments (optional filter)         | admin required                   |
| GET    | `/api/village-data`                      | Spielstadt config JSON (`village.ini`)      | public                           |
| GET    | `/api/village-data/logo`                 | Logo image (path from INI)                  | public                           |
| GET    | `/api/village-data/favicon`              | Favicon image (path from INI)               | public                           |


### API examples

The full list of the API calls is described in `[./docs/developer-guide.md](./docs/developer-guide.md)`.

With the LA-Server running at `http://localhost:5000`:

**List all employees**

```bash
curl http://localhost:5000/api/employees
```

**List only active employees**

```bash
curl http://localhost:5000/api/employees?active=true
```

**List job assignments**

```bash
curl http://localhost:5000/api/job-assignments
```

## Development

If you build or integrate a client, see [docs/developer-guide.md](docs/developer-guide.md) for the exact headers and flows. With the server running, **`GET /api/openapi.json`** serves the OpenAPI 3.0 schema and **`GET /api/docs`** serves Swagger UI (same host and port as the API).

- For developer information see: `[./docs/developer-guide.md](./docs/developer-guide.md)` — tools, API usage for client developers and backend notes for contributors.
- For information about the database layout see:   `[./docs/database_design.md](./docs/database_design.md)` — database schema and design.

## License

This project is released under the [MIT License](./LICENSE). Copyright © 2026 Kinderspielstadt Los Ämmerles e.V.
