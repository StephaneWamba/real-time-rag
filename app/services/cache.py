"""Redis caching service."""

import json
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import CacheError


class CacheService:
    """Service for caching query results and embeddings."""

    def __init__(self) -> None:
        """Initialize the cache service."""
        self.client: Optional[redis.Redis] = None
        self.ttl = settings.cache_ttl

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=settings.redis_pool_size,
                socket_connect_timeout=5.0,
            )
            await self.client.ping()
        except Exception as e:
            raise CacheError(f"Failed to connect to Redis: {str(e)}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[str]:
        """
        Get a value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        if not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time to live in seconds.
        """
        if not self.client:
            return
        try:
            await self.client.setex(key, ttl or self.ttl, value)
        except Exception as e:
            raise CacheError(f"Failed to set cache: {str(e)}") from e

    async def get_json(self, key: str) -> Optional[dict]:
        """
        Get a JSON value from cache.

        Args:
            key: Cache key.

        Returns:
            Parsed JSON value or None if not found.
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        """
        Set a JSON value in cache.

        Args:
            key: Cache key.
            value: Dictionary to cache.
            ttl: Time to live in seconds.
        """
        await self.set(key, json.dumps(value), ttl)

    async def delete(self, key: str) -> None:
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete.
        """
        if not self.client:
            return
        try:
            await self.client.delete(key)
        except Exception:
            pass
