# Kinderspielstadt Los Ämmerles - LA-Server

This project supports the [Kinderspielstadt](https://de.wikipedia.org/wiki/Kinderstadt) in Ammerbuch ([Los Ämmerles](https://los-aemmerles.de/)) to digitalize the summer camp.
Together with the connected clients (la-job-center, la-job-center-kiosk-mode, ...) the children apply for jobs during the camp.

The server is a Python Flask server with MariaDB database backend.
The production implementation with [waitress](https://github.com/Pylons/waitress) runs with 4 threads.


## Prerequisites

The **"Kinderspielstadt Los Ämmerles - LA-Server"** requires Python, installed on your local computer.
MariaDB can be installed locally or you can connect to a database installed on the internet.

The following versions are required to run the LA-Server:

- Python 3.14+
- MariaDB 10.6+

## Setup (Production, no Poetry)

1. **Clone or copy the GIT repository**

   The public repository URL is not published yet; use your team’s clone URL or a downloaded archive when available.

   Usually the copy is done with the git command: `git clone https://github.com/Dieter-W/la-server.git`
   You can also download a zip or tarball from [GitHub](https://github.com/Dieter-W/la-Server) to create the LA-Server directory.

2. **Initialize `.env`**

   Windows (PowerShell):

   ```powershell
   .\scripts\$setup.ps1 -Mode init-env
   ```

   Linux / macOS / Git Bash (make the script executable once: `chmod +x './scripts/$setup.sh'`):

   ```bash
   './scripts/$setup.sh' --mode init-env
   ```

   This creates `.env` from `.env.example` (if missing) and stops.

3. **Update `.env`**

   Set production values (at minimum `DEBUG=false`, `SECRET_KEY`, and MariaDB credentials).

4. **Provision environment**

   Windows (PowerShell):

   ```powershell
   .\scripts\$setup.ps1 -Mode provision
   ```

   Linux / macOS / Git Bash:

   ```bash
   './scripts/$setup.sh' --mode provision
   ```

   This checks that `.env` was customized, then creates or reuses `.venv`, installs dependencies from `data/requirements.txt`, and runs `scripts/create_database.py` unless you skip that step (see parameters below).

**Manual alternative (same as `provision` without the scripts):**

```bash
python3 -m venv .venv
source .venv/bin/activate   # Git Bash on Windows: source .venv/Scripts/activate
pip install -r data/requirements.txt
python ./scripts/create_database.py
```

### `$setup.ps1` parameters (Windows)

- `-Mode <init-env|provision>`: `init-env` creates `.env` and exits; `provision` runs full setup.
- `-RequirementsPath <string>`: Path to the production `requirements.txt`. Default: `.\data\requirements.txt`.
- `-SkipCreateDatabase`: Skip running `python .\scripts\create_database.py`.
- `-ForceRecreateVenv`: Delete `.\.venv` if it exists and recreate it before installing dependencies.

```powershell
.\scripts\$setup.ps1 -Mode init-env
.\scripts\$setup.ps1 -Mode provision
.\scripts\$setup.ps1 -Mode provision -SkipCreateDatabase
.\scripts\$setup.ps1 -Mode provision -ForceRecreateVenv -RequirementsPath ".\data\requirements.txt"
```

### `$setup.sh` parameters (Linux / macOS / Git Bash)

- `--mode <init-env|provision>`: Same as PowerShell `-Mode`.
- `--requirements-path <path>`: Path to the production `requirements.txt`. Default: `./data/requirements.txt` (relative to the project root).
- `--skip-create-database`: Skip `python ./scripts/create_database.py`.
- `--force-recreate-venv`: Remove `./.venv` and recreate it before installing dependencies.
- `-h` / `--help`: Show usage.

```bash
'./scripts/$setup.sh' --mode init-env
'./scripts/$setup.sh' --mode provision
'./scripts/$setup.sh' --mode provision --skip-create-database
'./scripts/$setup.sh' --mode provision --force-recreate-venv --requirements-path ./data/requirements.txt
```

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

**CSV format:** Comma-separated with a header row. Required columns: `company_name`, `jobs_max`, `pay_per_hour`, `active`, `notes`.

Example `company.csv`:

```csv
company_name,jobs_max,pay_per_hour,active,notes
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

To skip checksum validation on employee numbers (not recommended), pass `--nochecksum-check` as a second argument:

```bash
python ./scripts/bulk_import_employees.py employees.csv --nochecksum-check
```

**Note:**
It's useful to use employee numbers with checksums, otherwise a typo can refer to a different child.
A full explanation of how to create employee numbers with checksums in Excel is in `[./docs/employee-numbers.md](./docs/employee-numbers.md)`.

**CSV format:** Comma-separated with a header row. Required columns: `first_name`, `last_name`, `employee_number`, `role`, `active`, `notes`.

Example `employees.csv`:

```csv
first_name,last_name,employee_number,role,active,notes
Max,Mustermann,M00155,Betreuer,true,Works weekends
Anna,Schmidt,A00265,Helferin,true,
```

The script creates or updates employees (by `employee_number`) and logs successes and errors to stdout. It exits with a non-zero code if any row fails to import.


## Development

- For developer information see: `[./docs/developer-guide.md](./docs/developer-guide.md)` — tools, API usage for client developers and backend notes for contributors.
- For information about the database layout see:   `[./docs/README_Database_Design.md](./docs/README_Database_Design.md)` — database schema and design.

## API Endpoints


| Endpoint                                        | Description                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------------- |
| `GET /api/health`                               | Basic health check                                                        |
| `GET /api/health/db`                            | Database connectivity                                                     |
| `GET /api/health/runtime`                       | Operational diagnostics (pool, concurrency peaks, redacted DB URL; no customer data) |
| `GET /api/employees`                            | List all employees (optional `?active=true` or `?active=false`)           |
| `GET /api/employees/<employee_number>`          | Fetch a single employee                                                   |
| `POST /api/employees`                           | Create a new employee                                                     |
| `PUT /api/employees/<employee_number>`          | Update an employee                                                        |
| `DELETE /api/employees/<employee_number>`       | Soft delete (sets `active=false`); use `?hard=true` to permanently delete |
| `GET /api/companies`                            | List all companies (optional `?active=true` or `?active=false`)           |
| `GET /api/companies/<company_name>`             | Fetch a single company                                                    |
| `POST /api/companies`                           | Create a new company                                                      |
| `PUT /api/companies/<company_name>`             | Update a company                                                          |
| `DELETE /api/companies/<company_name>`          | Delete company permanently                                                |
| `GET /api/job-assignments`                      | List all job assignments                                                  |
| `POST /api/job-assignments`                     | Create a job assignment (JSON: `company_name`, `employee_number`)         |
| `DELETE /api/job-assignments/<employee_number>` | Remove the job assignment for that employee                               |
| `POST /api/job-assignments/reset`               | Reset assignments (optional JSON `company_name` to limit scope)           |


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

## License

This project is released under the [MIT License](./LICENSE). Copyright © 2026 Kinderspielstadt Los Ämmerles e.V.
