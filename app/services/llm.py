"""OpenAI LLM service for response generation with structured outputs."""

import json
from typing import List

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import LLMError
from app.models.response import StructuredAnswer


class LLMService:
    """Service for generating LLM responses with structured outputs."""

    def __init__(self) -> None:
        """Initialize the LLM service."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    async def generate_response(self, query: str, context: str, document_ids: List[str]) -> StructuredAnswer:
        """
        Generate a structured response using the LLM.

        Args:
            query: User query.
            context: Retrieved context from vector search.
            document_ids: List of document IDs used as context.

        Returns:
            Structured answer with metadata.

        Raises:
            LLMError: If response generation fails.
        """
        try:
            schema = StructuredAnswer.model_json_schema()

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on the provided context. "
                        "You MUST respond with valid JSON only, no other text. "
                        "Provide a confidence score (0-1) indicating how confident you are in your answer. "
                        "If the context doesn't contain enough information, set is_complete to false and explain what's missing. "
                        "Return citations as a list of document IDs that were used in your answer. "
                        f"Your response must be valid JSON matching this schema: {json.dumps(schema)}",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {query}\n\n"
                        f"Available document IDs: {', '.join(document_ids) if document_ids else 'None'}\n\n"
                        "Provide a structured answer with confidence score and citations as JSON only (no markdown, no code blocks).",
                    },
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMError("Empty response from LLM")

            data = json.loads(content)
            return StructuredAnswer(**data)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse LLM response as JSON: {str(e)}. Content: {content[:200]}") from e
        except (TypeError, ValueError) as e:
            raise LLMError(
                f"Failed to process LLM response: {str(e)}") from e
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"Failed to generate response: {str(e)}") from e

    async def generate_response_text(self, query: str, context: str) -> str:
        """
        Generate a simple text response.

        Args:
            query: User query.
            context: Retrieved context from vector search.

        Returns:
            Generated response text.
        """
        structured = await self.generate_response(query, context, [])
        return structured.answer
