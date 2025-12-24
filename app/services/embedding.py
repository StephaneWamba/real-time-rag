"""OpenAI embedding generation service."""

from typing import List

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import EmbeddingError


class EmbeddingService:
    """Service for generating embeddings using OpenAI."""

    def __init__(self) -> None:
        """Initialize the embedding service."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}") from e

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed.

        Returns:
            Embedding vector.
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]


