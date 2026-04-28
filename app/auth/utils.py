"""Utility functions for the authentication routes."""

from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token as jwt_create_access_token


def hash_password(password: str) -> str:
    """Hash a password using werkzeug."""
    return generate_password_hash(password)


def verify_password(stored_hash: str, plain_password: str) -> bool:
    """Verify `plain_password` against a werkzeug hash from the database."""
    return check_password_hash(stored_hash, plain_password)


def create_access_token(identity, additional_claims=None):
    """Create an access token for the given identity and additional claims.

    PyJWT requires JWT ``sub`` (identity) to be a string — we stringify here so
    callers can pass ints (e.g. DB primary keys).
    """
    if additional_claims is None:
        return jwt_create_access_token(identity=str(identity))
    return jwt_create_access_token(
        identity=str(identity), additional_claims=additional_claims
    )
