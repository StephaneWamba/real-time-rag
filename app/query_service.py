"""Query Service: RAG endpoint for answering questions."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.api.health import check_all_dependencies, check_readiness
from app.core.config import settings
from app.core.dependencies import services
from app.monitoring.metrics import (
    query_counter,
    query_duration_seconds,
    query_errors_total,
    query_latency_seconds,
)
from app.services.query_processor import QueryProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await services.initialize()
    logger.info("Query Service started")
    yield
    await services.shutdown()
    logger.info("Query Service stopped")


app = FastAPI(title="Query Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_processor = QueryProcessor(
    vector_db=services.vector_db,
    embedding_service=services.embedding_service,
    llm_service=services.llm_service,
    cache_service=services.cache_service,
)


class QueryRequest(BaseModel):
    """Query request model."""

    query: str
    top_k: int = settings.top_k
    page: int = 1
    page_size: int = 10


class QueryResponse(BaseModel):
    """Query response model."""

    answer: str
    sources: List[Dict]
    latency_ms: float
    confidence: float = 0.0
    is_complete: bool = True
    pagination: Optional[Dict] = None


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Process a RAG query.

    Args:
        request: Query request.

    Returns:
        Query response with answer and sources.
    """
    start_time = time.time()
    query_counter.inc()

    try:
        result = await query_processor.process_query(
            query=request.query,
            top_k=request.top_k,
            page=request.page,
            page_size=request.page_size,
        )

        latency_ms = (time.time() - start_time) * 1000
        latency_seconds = latency_ms / 1000
        query_latency_seconds.observe(latency_seconds)
        query_duration_seconds.observe(time.time() - start_time)
        
        # Track sample for real-time visualization
        from app.services.metrics_tracker import add_query_latency_sample
        add_query_latency_sample(latency_seconds)

        response = QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            latency_ms=latency_ms,
            confidence=result["confidence"],
            is_complete=result["is_complete"],
            pagination=result.get("pagination"),
        )

        logger.info(f"Query processed in {latency_ms:.2f}ms")
        return response

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        query_errors_total.inc()
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


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
    from app.monitoring.metrics import (
        query_counter,
        query_latency_seconds,
    )
    from app.services.metrics_tracker import get_query_latency_samples
    
    return {
        'queries': {
            'total': query_counter._value.get(),
            'latency_samples': get_query_latency_samples(10),
        },
    }


@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint with dependency verification.

    Returns:
        Health status with service dependencies.
    """
    result = await check_all_dependencies(
        services.vector_db, services.cache_service
    )
    return {"status": result["status"], "service": "query-service", **result}


@app.get("/collections")
async def list_collections() -> dict:
    """
    List all available collections.

    Returns:
        List of collection names.
    """
    try:
        collections = await services.vector_db.list_collections()
        return {"collections": collections}
    except Exception as e:
        logger.error(f"Failed to list collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ready")
async def readiness() -> dict:
    """
    Readiness check endpoint.

    Returns:
        Readiness status.
    """
    result = await check_readiness(services.vector_db, services.cache_service)
    return {"service": "query-service", **result}
