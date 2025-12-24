"""Event processing service for document updates."""

import logging
import time
from typing import Optional

from app.core.exceptions import VectorDBError
from app.models.event import DocumentEvent
from app.monitoring.metrics import (
    update_lag_seconds,
    update_processing_duration,
    update_errors_total,
    updates_total,
)
from app.services.cache import CacheService
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.retry import retry_with_backoff
from app.services.vector_db import VectorDBService

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes document update events."""

    def __init__(
        self,
        vector_db: VectorDBService,
        embedding_service: EmbeddingService,
        chunking_service: ChunkingService,
        cache_service: CacheService,
    ) -> None:
        """
        Initialize event processor.

        Args:
            vector_db: Vector database service.
            embedding_service: Embedding generation service.
            chunking_service: Document chunking service.
            cache_service: Cache service.
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.chunking_service = chunking_service
        self.cache_service = cache_service

    async def process_event(self, event_data: dict) -> None:
        """
        Process a document update event.

        Args:
            event_data: Kafka event payload.
        """
        try:
            event = self._parse_event(event_data)
            if not event:
                return

            updates_total.inc()

            if event.op == "d":
                await self._handle_delete(event)
            elif event.op in ("c", "u"):
                await self._handle_create_or_update(event)
            else:
                logger.warning(f"Unknown operation: {event.op}")

        except Exception as e:
            logger.error(f"Failed to process event: {str(e)}")
            update_errors_total.inc()
            raise

    def _parse_event(self, event_data: dict) -> Optional[DocumentEvent]:
        """
        Parse event data into DocumentEvent.

        Args:
            event_data: Raw event data.

        Returns:
            Parsed event or None if invalid.
        """
        op = event_data.get("__op") or event_data.get("op", "c")
        ts_ms = event_data.get("__source_ts_ms") or event_data.get("ts_ms")

        if event_data.get("__deleted") == "true":
            op = "d"

        filtered_data = {
            k: v for k, v in event_data.items() if not k.startswith("__")
        }

        if not filtered_data:
            logger.warning("Event data is empty after filtering, skipping")
            return None

        if op == "d":
            before_data = filtered_data
            after_data = None
        else:
            before_data = None
            after_data = filtered_data

        return DocumentEvent(
            op=op,
            before=before_data,
            after=after_data,
            source={},
            ts_ms=ts_ms or int(time.time() * 1000),
        )

    async def _handle_delete(self, event: DocumentEvent) -> None:
        """
        Handle document deletion.

        Args:
            event: Deletion event.
        """
        document_id = event.get_document_id()
        if not document_id:
            logger.warning("Delete event missing document ID")
            return

        try:
            await self.vector_db.delete_document_chunks(str(document_id))
            logger.info(f"Deleted chunks for document {document_id}")
        except VectorDBError as e:
            logger.error(f"Failed to delete chunks: {str(e)}")
            raise

    async def _handle_create_or_update(self, event: DocumentEvent) -> None:
        """
        Handle document create or update.

        Args:
            event: Create or update event.
        """
        if not event.after:
            logger.warning("Create/update event missing 'after' data")
            return

        document_id = event.after.get("id")
        content = event.after.get("content", "")
        version = event.after.get("version", 1)

        if not document_id or not content:
            logger.warning(
                f"Event missing required fields: id={document_id}, "
                f"content={'present' if content else 'missing'}"
            )
            return

        try:
            start_time = time.time()

            chunks = self.chunking_service.chunk_document(
                content, str(document_id))
            if not chunks:
                logger.warning(
                    f"No chunks generated for document {document_id}")
                return

            texts = [chunk["content"] for chunk in chunks]

            async def generate_embeddings():
                return await self.embedding_service.generate_embeddings(texts)

            embeddings = await retry_with_backoff(
                generate_embeddings,
                exceptions=(Exception,),
            )

            async def upsert_chunks():
                return await self.vector_db.upsert_chunks(
                    chunks, embeddings, str(document_id), version
                )

            await retry_with_backoff(
                upsert_chunks,
                exceptions=(VectorDBError,),
            )

            processing_time = time.time() - start_time
            update_processing_duration.observe(processing_time)

            event_timestamp = event.get_timestamp().timestamp()
            lag = time.time() - event_timestamp
            update_lag_seconds.observe(lag)
            
            # Track sample for real-time visualization
            from app.services.metrics_tracker import add_update_lag_sample
            add_update_lag_sample(lag)

            # Track pipeline activity for frontend
            try:
                from app.services.pipeline_tracker import update_pipeline_activity
                
                # Estimate stage latencies (simplified - in real system would track each stage)
                stage_latencies = {
                    'postgresql': 0.05,
                    'debezium': 0.10,
                    'kafka': 0.05,
                    'update_service': processing_time * 0.3,
                    'embedding': processing_time * 0.5,
                    'qdrant': processing_time * 0.2,
                }
                update_pipeline_activity(stage_latencies, str(document_id))
            except Exception:
                pass  # Don't fail if tracking fails

            await self.cache_service.delete(f"query:{document_id}")

            logger.info(
                f"Updated document {document_id} (version {version}) "
                f"in {processing_time:.2f}s, lag: {lag:.2f}s"
            )

        except Exception as e:
            logger.error(f"Failed to process create/update: {str(e)}")
            raise
