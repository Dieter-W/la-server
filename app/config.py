"""Application configuration."""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Runtime application configuration.

    Values are intentionally computed at access time (not as static class attributes)
    so tests/scripts can monkeypatch environment variables before app creation.
    """

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        val = os.getenv(name, "true" if default else "false")
        return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

    @classmethod
    def mariadb_host(cls) -> str:
        return os.getenv("MARIADB_HOST", "localhost")

    @classmethod
    def mariadb_port(cls) -> int:
        return int(os.getenv("MARIADB_PORT", "3306"))

    @classmethod
    def mariadb_user(cls) -> str:
        return os.getenv("MARIADB_USER", "root")

    @classmethod
    def mariadb_password(cls) -> str:
        return os.getenv("MARIADB_PASSWORD", "")

    @classmethod
    def mariadb_database(cls) -> str:
        return os.getenv("MARIADB_DATABASE", "kinderspielstadt")

    @classmethod
    def sqlalchemy_database_uri(cls) -> str:
        return (
            "mysql+pymysql://"
            f"{cls.mariadb_user()}:{cls.mariadb_password()}"
            f"@{cls.mariadb_host()}:{cls.mariadb_port()}/{cls.mariadb_database()}"
        )

    @classmethod
    def admin_db_uri(cls) -> str:
        return (
            "mysql+pymysql://"
            f"{cls.mariadb_user()}:{cls.mariadb_password()}"
            f"@{cls.mariadb_host()}:{cls.mariadb_port()}/mysql"
        )

    @classmethod
    def log_level(cls) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def log_file(cls) -> str | None:
        path = os.getenv("LOG_FILE", "").strip()
        return path or None

    @classmethod
    def get_config(cls) -> dict:
        """Return Flask config mapping computed from current environment."""

        return {
            "MARIADB_HOST": cls.mariadb_host(),
            "MARIADB_PORT": cls.mariadb_port(),
            "MARIADB_USER": cls.mariadb_user(),
            "MARIADB_PASSWORD": cls.mariadb_password(),
            "MARIADB_DATABASE": cls.mariadb_database(),
            "SECRET_KEY": os.getenv("SECRET_KEY", "-your-secret-key-here-is-32-char-"),
            "DEBUG": cls._env_bool("DEBUG", default=False),
            "VALIDATE_CHECK_SUM": cls._env_bool("VALIDATE_CHECK_SUM", default=True),
            "SQLALCHEMY_DATABASE_URI": cls.sqlalchemy_database_uri(),
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                "pool_recycle": 300,
            },
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "ADMIN_DB_URI": cls.admin_db_uri(),
            "TESTING": cls._env_bool("TESTING", default=False),
            "LOG_LEVEL": cls.log_level(),
            "LOG_FILE": cls.log_file(),
            "JWT_SECRET_KEY": os.getenv(
                "SECRET_KEY", "-your-secret-key-here-is-32-char-"
            ),
            "JWT_ACCESS_TOKEN_EXPIRES": timedelta(minutes=15),
            "JWT_REFRESH_TOKEN_EXPIRES": timedelta(hours=3),
        }
