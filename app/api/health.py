"""Health check utilities."""

from typing import Dict

from app.services.cache import CacheService
from app.services.health import (
    check_kafka,
    check_openai,
    check_postgres,
    check_qdrant,
    check_redis,
)
from app.services.vector_db import VectorDBService


async def check_all_dependencies(
    vector_db: VectorDBService,
    cache_service: CacheService,
    include_kafka: bool = False,
    include_postgres: bool = False,
) -> Dict:
    """
    Check all service dependencies.

    Args:
        vector_db: Vector database service.
        cache_service: Cache service.
        include_kafka: Whether to check Kafka.
        include_postgres: Whether to check PostgreSQL.

    Returns:
        Dictionary with overall status and individual service statuses.
    """
    services = {}
    overall_status = "healthy"

    qdrant_status = await check_qdrant(vector_db)
    services["qdrant"] = qdrant_status
    if qdrant_status.get("status") != "healthy":
        overall_status = "unhealthy"

    redis_status = await check_redis(cache_service)
    services["redis"] = redis_status
    if redis_status.get("status") != "healthy":
        overall_status = "unhealthy"

    openai_status = await check_openai()
    services["openai"] = openai_status
    if openai_status.get("status") == "unhealthy":
        overall_status = "unhealthy"

    if include_kafka:
        kafka_status = await check_kafka()
        services["kafka"] = kafka_status
        if kafka_status.get("status") != "healthy":
            overall_status = "unhealthy"

    if include_postgres:
        postgres_status = await check_postgres()
        services["postgres"] = postgres_status
        if postgres_status.get("status") != "healthy":
            overall_status = "unhealthy"

    return {"status": overall_status, "services": services}


async def check_readiness(
    vector_db: VectorDBService,
    cache_service: CacheService,
    include_kafka: bool = False,
    include_postgres: bool = False,
) -> Dict:
    """
    Check service readiness.

    Args:
        vector_db: Vector database service.
        cache_service: Cache service.
        include_kafka: Whether Kafka is required.
        include_postgres: Whether PostgreSQL is required.

    Returns:
        Readiness status dictionary.
    """
    qdrant_status = await check_qdrant(vector_db)
    redis_status = await check_redis(cache_service)

    ready = (
        qdrant_status.get("status") == "healthy"
        and redis_status.get("status") == "healthy"
    )

    result = {
        "ready": ready,
        "qdrant": qdrant_status.get("status") == "healthy",
        "redis": redis_status.get("status") == "healthy",
    }

    if include_kafka:
        kafka_status = await check_kafka()
        ready = ready and kafka_status.get("status") == "healthy"
        result["kafka"] = kafka_status.get("status") == "healthy"

    if include_postgres:
        postgres_status = await check_postgres()
        ready = ready and postgres_status.get("status") == "healthy"
        result["postgres"] = postgres_status.get("status") == "healthy"

    result["ready"] = ready
    return result
