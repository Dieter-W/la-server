"""Abstract base repository for type-hinting convenience."""

from __future__ import annotations
from typing import Generic, TypeVar

from sqlalchemy.orm import Session
from app.models import BaseModel

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------
# Base repository
# ---------------------------------------------------------------------
class BaseRepository(Generic[T]):
    def __init__(self, db: Session) -> None:
        """Attach the SQLAlchemy session used for queries."""
        self.db = db
