"""Update Service: Processes Kafka events and updates vector database."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.api.health import check_all_dependencies, check_readiness
from app.core.config import settings
from app.core.dependencies import services
from app.core.exceptions import DatabaseError
from app.models.document_api import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.dlq import DLQService
from app.services.event_processor import EventProcessor
from app.services.pipeline_tracker import get_pipeline_status
from app.monitoring.metrics import (
    updates_total,
    update_lag_seconds,
    update_processing_duration,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await services.initialize()
    logger.info("Update Service started")
    asyncio.create_task(consume_kafka_events())
    yield
    await services.shutdown()
    logger.info("Update Service stopped")


app = FastAPI(title="Update Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

event_processor = EventProcessor(
    vector_db=services.vector_db,
    embedding_service=services.embedding_service,
    chunking_service=services.chunking_service,
    cache_service=services.cache_service,
)


async def consume_kafka_events() -> None:
    """Consume events from Kafka."""
    from aiokafka import AIOKafkaConsumer

    consumer = AIOKafkaConsumer(
        settings.kafka_topic_documents,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="update-service",
    )

    await consumer.start()
    logger.info(
        f"Started consuming from topic: {settings.kafka_topic_documents}")

    try:
        async for message in consumer:
            try:
                if message.value is None:
                    logger.warning(
                        f"Message at offset {message.offset} has None value, skipping")
                    continue

                event_data = message.value
                if isinstance(event_data, dict) and "payload" in event_data:
                    event_data = event_data["payload"]

                if not isinstance(event_data, dict):
                    logger.warning(
                        f"Event data is not a dict: {type(event_data)}, skipping"
                    )
                    continue

                await event_processor.process_event(event_data)
            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"Error processing message at offset {message.offset}: {error_msg}"
                )

                try:
                    await services.dlq_service.send_failed_event(
                        event_data=event_data if isinstance(
                            event_data, dict) else {},
                        error=error_msg,
                        original_topic=settings.kafka_topic_documents,
                        offset=message.offset,
                        partition=message.partition,
                    )
                except Exception as dlq_error:
                    logger.error(
                        f"Failed to send event to DLQ: {str(dlq_error)}")
    finally:
        await consumer.stop()


@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint with dependency verification.

    Returns:
        Health status with service dependencies.
    """
    result = await check_all_dependencies(
        services.vector_db,
        services.cache_service,
        include_kafka=True,
        include_postgres=True,
    )
    return {"status": result["status"], "service": "update-service", **result}


@app.get("/ready")
async def readiness() -> dict:
    """
    Readiness check endpoint.

    Returns:
        Readiness status.
    """
    result = await check_readiness(
        services.vector_db,
        services.cache_service,
        include_kafka=True,
        include_postgres=True,
    )
    return {"service": "update-service", **result}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/metrics")
async def get_metrics_json() -> dict:
    """
    Get metrics in JSON format for frontend.

    Returns:
        Metrics summary.
    """
    metrics_data = {}
    
    metrics_data['updates_total'] = updates_total._value.get()
    metrics_data['update_errors_total'] = 0
    
    try:
        from app.services.metrics_tracker import get_update_lag_samples
        metrics_data['update_lag_samples'] = get_update_lag_samples(10)
    except Exception:
        metrics_data['update_lag_samples'] = []
    
    return {
        'updates': {
            'total': metrics_data.get('updates_total', 0),
            'lag_samples': metrics_data.get('update_lag_samples', []),
        },
        'last_update': get_pipeline_status().get('last_update'),
    }


@app.get("/api/pipeline/status")
async def get_pipeline_status_endpoint() -> dict:
    """
    Get current pipeline status.

    Returns:
        Pipeline status with stage latencies.
    """
    return get_pipeline_status()


@app.post("/process-event")
async def process_event_manual(event_data: dict) -> dict:
    """
    Manually process an event.

    Args:
        event_data: Event payload.

    Returns:
        Processing result.
    """
    try:
        await event_processor.process_event(event_data)
        return {"status": "processed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> DocumentListResponse:
    """
    List documents.

    Args:
        limit: Maximum number of documents to return.
        offset: Number of documents to skip.

    Returns:
        List of documents.
    """
    try:
        documents = await services.database.get_documents(limit=limit, offset=offset)
        total = await services.database.count_documents()
        return DocumentListResponse(
            documents=[DocumentResponse(**doc) for doc in documents],
            total=total,
            limit=limit,
            offset=offset,
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.get("/api/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str) -> DocumentResponse:
    """
    Get a document by ID.

    Args:
        document_id: Document UUID.

    Returns:
        Document details.
    """
    try:
        document = await services.database.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse(**document)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@app.post("/api/documents", response_model=DocumentResponse, status_code=201)
async def create_document(document: DocumentCreate) -> DocumentResponse:
    """
    Create a new document.

    Args:
        document: Document data.

    Returns:
        Created document.
    """
    try:
        created = await services.database.create_document(
            title=document.title, content=document.content
        )
        return DocumentResponse(**created)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")


@app.put("/api/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str, document: DocumentUpdate
) -> DocumentResponse:
    """
    Update a document.

    Args:
        document_id: Document UUID.
        document: Updated document data.

    Returns:
        Updated document.
    """
    try:
        updated = await services.database.update_document(
            document_id=document_id,
            title=document.title,
            content=document.content,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse(**updated)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


@app.delete("/api/documents/{document_id}", status_code=204)
async def delete_document(document_id: str) -> None:
    """
    Delete a document.

    Args:
        document_id: Document UUID.
    """
    try:
        deleted = await services.database.delete_document(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
