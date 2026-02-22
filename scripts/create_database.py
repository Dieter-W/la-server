"""Create the MariaDB database if it does not exist."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import pymysql

# Add project root to path and load .env
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

HOST = os.getenv("MARIADB_HOST", "localhost")
PORT = int(os.getenv("MARIADB_PORT", "3306"))
USER = os.getenv("MARIADB_USER", "root")
PASSWORD = os.getenv("MARIADB_PASSWORD", "")
DATABASE = os.getenv("MARIADB_DATABASE", "kinderspielstadt")


def create_database() -> None:
    """Create the database if it does not exist."""
    conn = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.commit()
        print(f"Database '{DATABASE}' is ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        create_database()
    except pymysql.Error as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
