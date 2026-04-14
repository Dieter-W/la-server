"""Process-local peak concurrency counters (thread-safe)."""

import threading


class PeakCounter:
    """Tracks active count and historic maximum concurrent enters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self._max_historic = 0

    def enter(self) -> None:
        with self._lock:
            self._active += 1
            if self._active > self._max_historic:
                self._max_historic = self._active

    def leave(self) -> None:
        with self._lock:
            self._active -= 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "active": self._active,
                "max_historic": self._max_historic,
            }
