"""Pydantic models for document API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Model for creating a document."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class DocumentUpdate(BaseModel):
    """Model for updating a document."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)


class DocumentResponse(BaseModel):
    """Model for document response."""

    id: str
    title: str
    content: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """Model for document list response."""

    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int
