# Kinderspielstadt Ammerbuch - Server

Python Flask server with MariaDB database backend.

## Prerequisites

- Python 3.11+
- MariaDB 10.6+

## Setup

1. **Create virtual environment**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # Linux/macOS
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   copy .env.example .env   # Windows
   cp .env.example .env     # Linux/macOS
   ```

   Edit `.env` and set your MariaDB credentials and other options.

4. **Create database**

   Run the script:
   ```bash
   python scripts/create_database.py
   ```
   
## Run

**Option 1 – Start scripts** (activate venv automatically):

```bash
.\start.ps1      # Windows PowerShell
./start.sh       # Linux/macOS (chmod +x start.sh first)
```

**Option 2 – Manual:**

```bash
python main.py
```

The server starts at `http://localhost:5000`.

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
   Set `MARIADB_HOST`, `MARIADB_USER`, `MARIADB_PASSWORD`, `MARIADB_DATABASE` for your production MariaDB instance.

### Optional environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5000` | Listen port |
| `THREADS` | `4` | Number of Waitress worker threads |

### Direct Waitress start

```bash
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 main:app
```

### Recommended for production

- **Reverse proxy** (Nginx, Apache, Caddy) in front of the app for SSL/TLS, static files, and load balancing.
- **Process manager** (systemd on Linux, Windows Service) for automatic restarts and supervision.

## API Endpoints

| Endpoint       | Description              |
|----------------|--------------------------|
| `GET /api/health`   | Basic health check       |
| `GET /api/health/db` | Database connectivity   |
| `GET /api/employees` | List all employees (optional `?active=true` or `?active=false`) |
| `GET /api/employees/<employee_number>` | Fetch a single employee |
| `POST /api/employees` | Create a new employee |
| `PUT /api/employees/<employee_number>` | Update an employee |
| `DELETE /api/employees/<employee_number>` | Soft delete (sets `active=false`); use `?hard=true` to permanently delete |
| `GET /api/companies` | List all companies optional `?active=true` or `?active=false`)|
| `GET /api/companies/<company_name>` | Fetch a single company |
| `POST /api/companies` | Create a new company |
| `PUT /api/companies/<company_name>` | Update an company |
| `DELETE /api/companies/<company_name>` | Delete company |

### Employee API examples

TODO: we have to create a seperate README to explain the endpoints in more detail

With the server running at `http://localhost:5000`:

**List all employees**
```bash
curl http://localhost:5000/api/employees
```

**List only active employees**
```bash
curl "http://localhost:5000/api/employees?active=true"
```

**Get a single employee**
```bash
curl http://localhost:5000/api/employees/M00155
```

**Create an employee**
```bash
curl -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -d "{\"first_name\":\"Max\",\"last_name\":\"Mustermann\",\"employee_number\":\"M00155\",\"role\":\"Betreuer\",\"active\":true,\"notes\":\"Works weekends\"}"
```

**Update an employee**
```bash
curl -X PUT http://localhost:5000/api/employees/M00155 \
  -H "Content-Type: application/json" \
  -d "{\"active\":true,\"notes\":\"Works Sundays\"}"
```

**Soft delete (deactivate) an employee**
```bash
curl -X DELETE http://localhost:5000/api/employees/M00155
```

**Hard delete (permanently remove) an employee**
```bash
curl -X DELETE "http://localhost:5000/api/employees/M00155?hard=true"
```

### CSV bulk import

Import companies from a CSV file:

```bash
python ./scripts/bulk_import_companies.py employees.csv 
```

**CSV format:** Comma-separated with a header row. Required columns: `company_name`, `number_of_jobs`, `pay_per_hour`, `active`, `notes`.

Example `company.csv`:
```csv
company_name,number_of_jobs,pay_per_hour,active,notes
Bank,8,10,true,,
Arbeitsamt,7,10,true,
Bauhof,8,10,true,
Küche,10,15,false,Only weekdays
```

The script creates or updates companies (by company_name) and logs successes and errors to stdout. It exits with a non-zero code if any row fails to import.

Import employees from a CSV file:

```bash
python ./scripts/bulk_import_employees.py employees.csv (optional `--nochecksum-check`)
```

**CSV format:** Comma-separated with a header row. Required columns: `first_name`, `last_name`, `employee_number`, `role`, `active`, `notes`.

Example `employees.csv`:
```csv
first_name,last_name,employee_number,role,active,notes
Max,Mustermann,M00155,Betreuer,true,Works weekends
Anna,Schmidt,A00265,Helferin,true,
```

The script creates or updates employees (by employee_number) and logs successes and errors to stdout. It exits with a non-zero code if any row fails to import.

## Test endpoints

TODO: enhance the test discription

The test is done with pytest:

```bash
pytest
```

## Project Structure

```
Server/
├── scripts/
│   ├── bulk_import_companies.py        # Import companies from CSV
│   ├── bulk_import_employees.py        # Import employees from CSV
│   └── create_database.py              # Create MariaDB database│   
├── app/
│   ├── __init__.py                     # App factory
│   ├── config.py                       # Configuration
│   ├── database.py                     # SQLAlchemy setup
│   ├── errors.py                       # Error handler
│   ├── models.py                       # Database models
│   └── routes/                         # API routes
├── tests/
│   ├── conftest.py                     # ??
│   ├── test_01_environment.py          # Test the environment
|   ├── test_02_health.py               # Test basic functions
|   ├── test_05_bulk_import_company.py  # Test the bulk import for companies
|   ├── test_05_bulk_import_employee.py # Test the bulk import for employies
|   ├── test_10_company.py              # Test company entpoints
|   └── test_11_employee.py             # test employee entpoints
├── main.py                             # Entry point
├── start.ps1                           # Start server (PowerShell)
├── start.sh                            # Start server (Linux/macOS)
├── requirements.txt
├── pytest.ini                          
├── .env.example
└── README.md
```

## Adding Models

Define new models in `app/models.py` inheriting from `BaseModel`:

```python
class YourModel(BaseModel):
    __tablename__ = "your_table"
    name = db.Column(db.String(255), nullable=False)
```

Tables are created automatically on first run.
