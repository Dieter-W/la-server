# Kinderspielstadt Ammerbuch Server

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

   Either run the script:
   ```bash
   python scripts/create_database.py
   ```
   Or create manually in MariaDB:
   ```sql
   CREATE DATABASE kinderspielstadt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

## Run

**Option 1 – Start scripts** (activate venv automatically):

```bash
.\start.bat      # Windows CMD
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
| `GET /api/employees` | List employees (optional `?active=true` or `?active=false`) |
| `GET /api/employees/<id>` | Fetch a single employee |
| `POST /api/employees` | Create a new employee |
| `PUT /api/employees/<id>` | Update an employee |
| `DELETE /api/employees/<id>` | Soft delete (set `active=false`); use `?hard=true` to permanently delete |

### Employee API examples

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
curl http://localhost:5000/api/employees/1
```

**Create an employee**
```bash
curl -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -d "{\"first_name\":\"Max\",\"last_name\":\"Mustermann\",\"employee_number\":\"M001\",\"role\":\"Betreuer\",\"active\":true,\"notes\":\"Works weekends\"}"
```

**Update an employee**
```bash
curl -X PUT http://localhost:5000/api/employees/1 \
  -H "Content-Type: application/json" \
  -d "{\"employee_number\":\"M001-UPD\",\"active\":true}"
```

**Soft delete (deactivate) an employee**
```bash
curl -X DELETE http://localhost:5000/api/employees/1
```

**Hard delete (permanently remove) an employee**
```bash
curl -X DELETE "http://localhost:5000/api/employees/1?hard=true"
```

### CSV bulk import

Import employees from a CSV file:

```bash
python scripts/bulk_import_employees.py employees.csv
```

**CSV format:** Comma-separated with a header row. Required columns: `first_name`, `last_name`, `employee_number`, `role`, `active`, `notes`.

Example `employees.csv`:
```csv
first_name,last_name,employee_number,role,active,notes
Max,Mustermann,M001,Betreuer,true,Works weekends
Anna,Schmidt,A002,Helferin,true,
```

The script creates or updates employees (by employee_number) and logs successes and errors to stdout. It exits with a non-zero code if any row fails to import.

## Test endpoints

With the server running, call:

```bash
python scripts/test_endpoints.py
```

Optional: pass a base URL to test another host/port:

```bash
python scripts/test_endpoints.py http://localhost:5000
```

## Project Structure

```
Server/
├── scripts/
│   ├── bulk_import_employees.py  # Import employees from CSV
│   ├── create_database.py       # Create MariaDB database
│   └── test_endpoints.py        # Test API endpoints
├── app/
│   ├── __init__.py      # App factory
│   ├── config.py        # Configuration
│   ├── database.py      # SQLAlchemy setup
│   ├── models.py        # Database models
│   └── routes/          # API routes
├── main.py              # Entry point
├── start.bat            # Start server (Windows CMD)
├── start.ps1            # Start server (PowerShell)
├── start.sh             # Start server (Linux/macOS)
├── requirements.txt
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
