"""Query processing service for RAG queries."""

import hashlib
import logging
from typing import Dict, List, Optional

from app.core.config import settings
from app.services.cache import CacheService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.vector_db import VectorDBService

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 8000
MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * 4
MIN_SIMILARITY_SCORE = 0.15


class QueryProcessor:
    """Processes RAG queries."""

    def __init__(
        self,
        vector_db: VectorDBService,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        cache_service: CacheService,
    ) -> None:
        """
        Initialize query processor.

        Args:
            vector_db: Vector database service.
            embedding_service: Embedding generation service.
            llm_service: LLM service.
            cache_service: Cache service.
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.cache_service = cache_service

    def _get_cache_key(self, query: str) -> str:
        """
        Generate cache key for a query.

        Args:
            query: User query.

        Returns:
            Cache key string.
        """
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_version = "v2"
        return f"query_response:{cache_version}:{query_hash}"

    def _build_context(self, matches: List[Dict]) -> tuple[str, List[Dict]]:
        """
        Build context from matches with token limits.

        Args:
            matches: List of matching chunks.

        Returns:
            Tuple of (context string, used matches).
        """
        context_parts = []
        total_chars = 0
        used_matches = []

        for match in matches:
            content = match.get("content", "")
            content_length = len(content)
            separator_length = 2 if context_parts else 0

            if total_chars + content_length + separator_length <= MAX_CONTEXT_CHARS:
                context_parts.append(content)
                total_chars += content_length + separator_length
                used_matches.append(match)
            else:
                remaining_space = MAX_CONTEXT_CHARS - total_chars - separator_length
                if remaining_space > 100:
                    truncated = content[:remaining_space]
                    context_parts.append(truncated)
                    used_matches.append(match)
                break

        return "\n\n".join(context_parts), used_matches

    def _filter_sources(
        self, sources: List[Dict], confidence: float, is_complete: bool
    ) -> List[Dict]:
        """
        Filter sources based on confidence and similarity.

        Args:
            sources: List of source dictionaries.
            confidence: LLM confidence score.
            is_complete: Whether answer is complete.

        Returns:
            Filtered sources list.
        """
        if confidence == 0.0:
            return []
        elif confidence < 0.3 or not is_complete:
            return [
                s
                for s in sources
                if s["cited"] and s["score"] >= MIN_SIMILARITY_SCORE
            ]
        else:
            return [s for s in sources if s["score"] >= MIN_SIMILARITY_SCORE]

    def _paginate_sources(
        self, sources: List[Dict], page: int, page_size: int
    ) -> tuple[List[Dict], Optional[Dict]]:
        """
        Paginate sources list.

        Args:
            sources: List of sources.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (paginated sources, pagination metadata).
        """
        total_sources = len(sources)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_sources = sources[start_idx:end_idx]

        pagination = None
        if total_sources > page_size:
            pagination = {
                "page": page,
                "page_size": page_size,
                "total": total_sources,
                "total_pages": (total_sources + page_size - 1) // page_size,
                "has_next": end_idx < total_sources,
                "has_prev": page > 1,
            }

        return paginated_sources, pagination

    async def process_query(
        self, query: str, top_k: int, page: int = 1, page_size: int = 10
    ) -> Dict:
        """
        Process a RAG query.

        Args:
            query: User query.
            top_k: Number of top matches to retrieve.
            page: Page number for pagination.
            page_size: Items per page.

        Returns:
            Query response dictionary.
        """
        cache_key = self._get_cache_key(query)
        cached_response = await self.cache_service.get_json(cache_key)

        if cached_response:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached_response

        query_embedding = await self.embedding_service.generate_embedding(query)
        matches = await self.vector_db.search(query_embedding, top_k=top_k)

        if not matches:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "sources": [],
                "confidence": 0.0,
                "is_complete": False,
            }

        matches = sorted(matches, key=lambda x: x.get(
            "score", 0), reverse=True)
        context, used_matches = self._build_context(matches)

        document_ids = [
            str(match["document_id"])
            for match in used_matches
            if match.get("document_id")
        ]
        structured_response = await self.llm_service.generate_response(
            query, context, document_ids
        )

        sources = [
            {
                "document_id": match["document_id"],
                "score": match["score"],
                "version": match["version"],
                "cited": str(match["document_id"]) in structured_response.citations,
            }
            for match in used_matches
        ]

        sources = self._filter_sources(
            sources,
            structured_response.confidence,
            structured_response.is_complete,
        )

        paginated_sources, pagination = self._paginate_sources(
            sources, page, page_size)

        response = {
            "answer": structured_response.answer,
            "sources": paginated_sources,
            "confidence": structured_response.confidence,
            "is_complete": structured_response.is_complete,
            "pagination": pagination,
        }

        await self.cache_service.set_json(
            cache_key, response, ttl=settings.cache_ttl
        )

        return response
