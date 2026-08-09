"""Abstract base repository for type-hinting convenience."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import BaseModel


# ---------------------------------------------------------------------
# Base repository
# ---------------------------------------------------------------------
class BaseRepository[T: BaseModel]:
    def __init__(self, db: Session) -> None:
        """Attach the SQLAlchemy session used for queries."""
        self.db = db
