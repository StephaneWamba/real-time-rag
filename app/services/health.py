"""Health check service for dependency verification."""

import time
from typing import Dict, Optional

from app.core.config import settings
from app.services.cache import CacheService
from app.services.vector_db import VectorDBService


async def check_qdrant(vector_db: VectorDBService) -> Dict[str, any]:
    """
    Check Qdrant connectivity and health.

    Args:
        vector_db: VectorDBService instance.

    Returns:
        Health status dictionary.
    """
    try:
        start_time = time.time()
        if not vector_db.client:
            return {"status": "unhealthy", "error": "Not connected", "latency_ms": 0}

        collections = await vector_db.client.get_collections()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "collections": len(collections.collections),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": 0,
        }


async def check_redis(cache_service: CacheService) -> Dict[str, any]:
    """
    Check Redis connectivity and health.

    Args:
        cache_service: CacheService instance.

    Returns:
        Health status dictionary.
    """
    try:
        start_time = time.time()
        if not cache_service.client:
            return {"status": "unhealthy", "error": "Not connected", "latency_ms": 0}

        await cache_service.client.ping()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": 0,
        }


async def check_openai() -> Dict[str, any]:
    """
    Check OpenAI API connectivity.

    Returns:
        Health status dictionary.
    """
    try:
        if not settings.openai_api_key:
            return {"status": "not_configured", "error": "API key not set"}

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        start_time = time.time()
        await client.models.list()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "authentication" in error_msg:
            return {"status": "unhealthy", "error": "Invalid API key"}
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": 0,
        }


async def check_kafka() -> Dict[str, any]:
    """
    Check Kafka connectivity.

    Returns:
        Health status dictionary.
    """
    try:
        from aiokafka import AIOKafkaConsumer
        import asyncio

        start_time = time.time()
        consumer = AIOKafkaConsumer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )

        await consumer.start()
        latency_ms = (time.time() - start_time) * 1000

        try:
            await asyncio.wait_for(consumer.stop(), timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception:
            pass

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": 0,
        }


async def check_postgres() -> Dict[str, any]:
    """
    Check PostgreSQL connectivity.

    Returns:
        Health status dictionary.
    """
    try:
        import asyncpg

        start_time = time.time()
        conn = await asyncpg.connect(settings.postgres_url)
        await conn.execute("SELECT 1")
        await conn.close()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": 0,
        }
