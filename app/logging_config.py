"""Thread-safe application logging.

Waitress worker threads emit records through a queue; a dedicated
:class:`logging.handlers.QueueListener` forwards them to handlers in a
single thread, which matches the stdlib logging cookbook pattern for
multi-threaded programs and avoids lock contention on file output.
"""

from __future__ import annotations

import atexit
import logging
import queue
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path

from flask import Flask

_DEFAULT_FORMAT = "%(asctime)s [%(threadName)s] %(name)s %(levelname)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_listener: QueueListener | None = None
_atexit_registered = False


def _level_from_name(name: str) -> int:
    key = name.upper().strip()
    mapping = logging.getLevelNamesMapping()
    if key in mapping:
        return mapping[key]
    try:
        return int(key)
    except ValueError:
        return logging.INFO


def _stop_listener() -> None:
    global _listener
    if _listener is not None:
        try:
            _listener.stop()
        finally:
            _listener = None


def configure_logging(app: Flask) -> None:
    """Configure ``app.logger`` for multi-threaded WSGI.

    Non-test runs use ``QueueHandler`` + ``QueueListener``. Tests use a simple
    stderr handler to avoid background listener lifecycle across app restarts.
    """
    global _listener, _atexit_registered

    if _listener is not None:
        _listener.stop()
        _listener = None

    log_level = _level_from_name(str(app.config.get("LOG_LEVEL", "INFO")))
    log_file = app.config.get("LOG_FILE")
    if isinstance(log_file, str) and not log_file.strip():
        log_file = None

    app.logger.handlers.clear()
    app.logger.setLevel(log_level)
    app.logger.propagate = False

    formatter = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT)

    if app.config.get("TESTING"):
        stderr = logging.StreamHandler()
        stderr.setFormatter(formatter)
        stderr.setLevel(log_level)
        app.logger.addHandler(stderr)
        return

    out_handlers: list[logging.Handler] = []
    stderr = logging.StreamHandler()
    stderr.setFormatter(formatter)
    stderr.setLevel(log_level)
    out_handlers.append(stderr)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        out_handlers.append(file_handler)

    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(log_level)
    app.logger.addHandler(queue_handler)

    _listener = QueueListener(
        log_queue,
        *out_handlers,
        respect_handler_level=True,
    )
    _listener.start()
    if not _atexit_registered:
        atexit.register(_stop_listener)
        _atexit_registered = True
