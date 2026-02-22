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
│   ├── create_database.py   # Create MariaDB database
│   └── test_endpoints.py    # Test API endpoints
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
