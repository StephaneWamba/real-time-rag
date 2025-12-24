"""Kafka event models for CDC changes."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentEvent(BaseModel):
    """Kafka event model for document changes."""

    op: str
    before: Optional[dict] = None
    after: Optional[dict] = None
    source: Optional[dict] = None
    ts_ms: Optional[int] = None

    def get_document_id(self) -> Optional[UUID]:
        """Extract document ID from event."""
        data = self.after or self.before
        if data and "id" in data:
            return UUID(data["id"])
        return None

    def get_timestamp(self) -> datetime:
        """Convert event timestamp to datetime."""
        if self.ts_ms:
            return datetime.fromtimestamp(self.ts_ms / 1000)
        # Fallback to current time if ts_ms not available
        return datetime.now()
