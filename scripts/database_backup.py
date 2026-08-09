#!/usr/bin/env python
"""Create and restore logical SQL backups of the LA-Server MariaDB database.

Connection settings are loaded from the project-root ``.env`` by default. Values
already present in the process environment take precedence. The utility delegates
SQL generation and import to MariaDB's native command-line clients, using
``mysqldump`` and ``mysql`` as compatible fallbacks.

Backups use a single transaction for a consistent snapshot of transactional
tables and include routines, triggers, and events. Restore imports the SQL into
the configured database; it does not create or drop the database itself.

Run ``python scripts/database_backup.py --help`` for usage and examples.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for backup and restore operations."""
    parser = argparse.ArgumentParser(
        description=(
            "Back up or restore the MariaDB database configured in .env. "
            "Native MariaDB/MySQL client tools are discovered automatically."
        ),
        epilog=(
            "examples:\n"
            "  python scripts/database_backup.py backup\n"
            "  python scripts/database_backup.py backup backups/pre-upgrade.sql\n"
            "  python scripts/database_backup.py restore backups/pre-upgrade.sql\n"
            "  python scripts/database_backup.py --env-file .env.production backup\n"
            "\n"
            "Run '<command> --help' for command-specific options."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="environment file to load (default: project-root .env)",
    )

    subparsers = parser.add_subparsers(dest="action", required=True)

    backup_parser = subparsers.add_parser(
        "backup",
        help="create an SQL backup",
        description=(
            "Create a consistent logical SQL backup. The default filename contains "
            "the database name and local timestamp."
        ),
    )
    backup_parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="output SQL file (default: backups/<database>_<timestamp>.sql)",
    )
    backup_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the output file if it already exists",
    )

    restore_parser = subparsers.add_parser(
        "restore",
        help="restore an SQL backup into the configured database",
        description=(
            "Import an SQL backup into the configured database. Stop LA-Server "
            "before restoring. Interactive confirmation is required by default."
        ),
    )
    restore_parser.add_argument("backup_file", type=Path, help="SQL backup to restore")
    restore_parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the destructive-operation confirmation prompt",
    )

    return parser


def find_executable(candidates: tuple[str, ...]) -> str:
    """Return the first available client executable or raise a clear error.

    The normal ``PATH`` is searched first. On Windows, ``MARIADB_BIN`` and common
    MariaDB, MySQL Server, and XAMPP installation directories are also checked.
    """
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            return executable

    if os.name == "nt":
        search_directories: list[Path] = []
        configured_bin = os.getenv("MARIADB_BIN", "").strip()
        if configured_bin:
            search_directories.append(Path(configured_bin).expanduser())

        program_files_roots = {
            Path(value)
            for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")
            if (value := os.getenv(variable))
        }
        for root in program_files_roots:
            search_directories.extend(root.glob("MariaDB */bin"))
            search_directories.extend(root.glob("MySQL/MySQL Server */bin"))

        search_directories.append(Path("C:/xampp/mysql/bin"))
        for directory in search_directories:
            for candidate in candidates:
                executable_path = directory / f"{candidate}.exe"
                if executable_path.is_file():
                    return str(executable_path)

    names = " or ".join(candidates)
    raise RuntimeError(
        f"Could not find {names}. Install the MariaDB client tools or set "
        "MARIADB_BIN to their bin directory."
    )


def load_database_settings(env_file: Path) -> dict[str, str]:
    """Load and validate MariaDB connection settings from an environment file.

    Existing process environment variables intentionally take precedence over
    values in ``env_file``, matching python-dotenv's default behavior.
    """
    env_file = env_file.expanduser().resolve()
    if not env_file.is_file():
        raise RuntimeError(f"Environment file not found: {env_file}")

    load_dotenv(env_file, override=False)
    settings = {
        "host": os.getenv("MARIADB_HOST", "localhost").strip(),
        "port": os.getenv("MARIADB_PORT", "3306").strip(),
        "user": os.getenv("MARIADB_USER", "root").strip(),
        "password": os.getenv("MARIADB_PASSWORD", ""),
        "database": os.getenv("MARIADB_DATABASE", "kinderspielstadt").strip(),
    }

    for key in ("host", "port", "user", "database"):
        if not settings[key]:
            raise RuntimeError(f"MARIADB_{key.upper()} must not be empty.")
    try:
        port = int(settings["port"])
    except ValueError as error:
        raise RuntimeError("MARIADB_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("MARIADB_PORT must be between 1 and 65535.")

    return settings


def client_environment(password: str) -> dict[str, str]:
    """Return a child-process environment containing the database password.

    ``MYSQL_PWD`` avoids exposing the password in the process command line. The
    value is passed only to the spawned MariaDB/MySQL client process.
    """
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = password
    return environment


def connection_arguments(settings: dict[str, str]) -> list[str]:
    """Build shared TCP connection arguments without embedding the password."""
    return [
        f"--host={settings['host']}",
        f"--port={settings['port']}",
        f"--user={settings['user']}",
        "--protocol=TCP",
    ]


def default_backup_path(database: str) -> Path:
    """Return a timestamped path in the project-root backup directory."""
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_BACKUP_DIR / f"{database}_{timestamp}.sql"


def create_backup(
    settings: dict[str, str], output: Path | None, *, force: bool
) -> None:
    """Write a logical SQL backup and remove partial output after failure.

    Existing output is preserved unless ``force`` is true. Relative output paths
    are interpreted from the caller's current working directory.
    """
    dump_executable = find_executable(("mariadb-dump", "mysqldump"))
    output_path = (output or default_backup_path(settings["database"])).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path = output_path.resolve()

    if output_path.exists() and not force:
        raise RuntimeError(
            f"Backup already exists: {output_path}. Use --force to overwrite it."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        dump_executable,
        *connection_arguments(settings),
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        settings["database"],
    ]

    try:
        with output_path.open("wb") as output_file:
            result = subprocess.run(
                command,
                stdout=output_file,
                stderr=subprocess.PIPE,
                env=client_environment(settings["password"]),
                check=False,
            )
        if result.returncode != 0:
            output_path.unlink(missing_ok=True)
            message = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"Backup failed: {message or 'unknown client error'}")
    except OSError:
        output_path.unlink(missing_ok=True)
        raise

    print(f"Backup created: {output_path}")


def confirm_restore(database: str, backup_file: Path) -> bool:
    """Require the operator to type the target database name."""
    print(f"This will restore '{backup_file}' into database '{database}'.")
    answer = input("Type the database name to continue: ").strip()
    return answer == database


def restore_backup(
    settings: dict[str, str], backup_file: Path, *, assume_yes: bool
) -> None:
    """Import an SQL file into the configured database.

    Confirmation is skipped only when ``assume_yes`` is true. The SQL file is
    streamed directly to the native client and is not loaded into Python memory.
    """
    client_executable = find_executable(("mariadb", "mysql"))
    backup_path = backup_file.expanduser().resolve()
    if not backup_path.is_file():
        raise RuntimeError(f"Backup file not found: {backup_path}")

    if not assume_yes and not confirm_restore(settings["database"], backup_path):
        raise RuntimeError("Restore cancelled; database name did not match.")

    command = [
        client_executable,
        *connection_arguments(settings),
        f"--database={settings['database']}",
        "--default-character-set=utf8mb4",
    ]
    with backup_path.open("rb") as input_file:
        result = subprocess.run(
            command,
            stdin=input_file,
            stderr=subprocess.PIPE,
            env=client_environment(settings["password"]),
            check=False,
        )
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"Restore failed: {message or 'unknown client error'}")

    print(f"Restore completed from: {backup_path}")


def main() -> int:
    """Run the selected operation and translate expected failures to exit codes."""
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()
    try:
        settings = load_database_settings(args.env_file)
        if args.action == "backup":
            create_backup(settings, args.output, force=args.force)
        else:
            restore_backup(settings, args.backup_file, assume_yes=args.yes)
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
