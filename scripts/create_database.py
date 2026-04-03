"""Create the MariaDB database and tables (e.g. employees) if they do not exist."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import pymysql

from sqlalchemy import create_engine, text

# Add project root to path and load .env
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402

load_dotenv(project_root / ".env")


def create_database() -> None:
    """Create the database if it does not exist."""

    # def db_create(env_patch):
    engine = create_engine(Config.admin_db_uri())
    with engine.connect() as conn:
        mariadb_db = os.getenv("MARIADB_DATABASE")
        conn.execute(text(f"CREATE DATABASE `{mariadb_db}`"))


def create_tables() -> None:
    """Create all tables (e.g. employees) via SQLAlchemy."""

    create_app(Config)  # init_db() inside create_app runs db.create_all()
    print("Tables created (employees and any other models).")


if __name__ == "__main__":
    try:
        create_database()
        create_tables()
        sys.exit(0)
    except pymysql.Error as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
