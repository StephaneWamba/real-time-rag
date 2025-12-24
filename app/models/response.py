"""Structured response models for LLM outputs."""

from typing import List

from pydantic import BaseModel, Field


class StructuredAnswer(BaseModel):
    """Structured answer from LLM with metadata."""

    answer: str = Field(description="The answer to the user's question")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    citations: List[str] = Field(
        default_factory=list, description="List of document IDs cited in the answer"
    )
    is_complete: bool = Field(
        description="Whether the answer is complete or partial based on available context"
    )
