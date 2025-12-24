"""Document models for the RAG system."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Document model representing a source document."""

    id: UUID
    title: str
    content: str
    updated_at: datetime
    version: int = Field(default=1, ge=1)

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentChunk(BaseModel):
    """Chunk model representing a document fragment."""

    id: str
    document_id: UUID
    content: str
    chunk_index: int
    metadata: dict = Field(default_factory=dict)
