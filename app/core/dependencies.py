"""Dependency injection for services."""

from app.services.cache import CacheService
from app.services.chunking import ChunkingService
from app.services.database import DatabaseService
from app.services.dlq import DLQService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.vector_db import VectorDBService


class ServiceContainer:
    """Container for service instances."""

    def __init__(self) -> None:
        """Initialize service container."""
        self.vector_db = VectorDBService()
        self.embedding_service = EmbeddingService()
        self.chunking_service = ChunkingService()
        self.cache_service = CacheService()
        self.llm_service = LLMService()
        self.dlq_service = DLQService()
        self.database = DatabaseService()

    async def initialize(self) -> None:
        """Initialize all services."""
        await self.vector_db.connect()
        await self.cache_service.connect()
        await self.database.connect()
        if self.dlq_service.enabled:
            await self.dlq_service.connect()

    async def shutdown(self) -> None:
        """Shutdown all services."""
        if self.dlq_service.enabled:
            await self.dlq_service.disconnect()
        await self.database.disconnect()
        await self.vector_db.disconnect()
        await self.cache_service.disconnect()


services = ServiceContainer()
