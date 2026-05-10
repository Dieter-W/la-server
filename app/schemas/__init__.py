"""Request/response DTOs for all resources."""

# ---------------------------------------------------------------------
# Partial-update sentinel
# ---------------------------------------------------------------------
_UNSET: object = object()
"""Sentinel: field omitted in partial-update payloads; check with ``field in req``."""
