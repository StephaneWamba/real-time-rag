"""Database service for PostgreSQL operations."""

import asyncpg
from typing import List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.exceptions import DatabaseError


class DatabaseService:
    """Service for PostgreSQL database operations."""

    def __init__(self) -> None:
        """Initialize database service."""
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                settings.postgres_url,
                min_size=2,
                max_size=10,
            )
        except Exception as e:
            raise DatabaseError(
                f"Failed to connect to database: {str(e)}") from e

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def count_documents(self) -> int:
        """
        Count total number of documents.

        Returns:
            Total document count.
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                return count
        except Exception as e:
            raise DatabaseError(f"Failed to count documents: {str(e)}") from e

    async def get_documents(
        self, limit: int = 100, offset: int = 0
    ) -> List[dict]:
        """
        Get list of documents.

        Args:
            limit: Maximum number of documents to return.
            offset: Number of documents to skip.

        Returns:
            List of document dictionaries.
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, title, content, version, created_at, updated_at
                    FROM documents
                    ORDER BY updated_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
                return [
                    {
                        "id": str(row["id"]),
                        "title": row["title"],
                        "content": row["content"],
                        "version": row["version"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            raise DatabaseError(f"Failed to fetch documents: {str(e)}") from e

    async def get_document(self, document_id: str) -> Optional[dict]:
        """
        Get a single document by ID.

        Args:
            document_id: Document UUID.

        Returns:
            Document dictionary or None if not found.
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, title, content, version, created_at, updated_at
                    FROM documents
                    WHERE id = $1
                    """,
                    document_id,
                )
                if row:
                    result = dict(row)
                    result["id"] = str(result["id"])
                    return result
                return None
        except Exception as e:
            raise DatabaseError(f"Failed to fetch document: {str(e)}") from e

    async def create_document(
        self, title: str, content: str
    ) -> dict:
        """
        Create a new document.

        Args:
            title: Document title.
            content: Document content.

        Returns:
            Created document dictionary.
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO documents (title, content, version)
                    VALUES ($1, $2, 1)
                    RETURNING id, title, content, version, created_at, updated_at
                    """,
                    title,
                    content,
                )
                result = dict(row)
                result["id"] = str(result["id"])
                return result
        except Exception as e:
            raise DatabaseError(f"Failed to create document: {str(e)}") from e

    async def update_document(
        self, document_id: str, title: Optional[str] = None, content: Optional[str] = None
    ) -> Optional[dict]:
        """
        Update a document.

        Args:
            document_id: Document UUID.
            title: New title (optional).
            content: New content (optional).

        Returns:
            Updated document dictionary or None if not found.
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        if not title and not content:
            raise DatabaseError(
                "At least one field (title or content) must be provided")

        try:
            async with self.pool.acquire() as conn:
                updates = []
                params = []
                param_idx = 1

                if title:
                    updates.append(f"title = ${param_idx}")
                    params.append(title)
                    param_idx += 1

                if content:
                    updates.append(f"content = ${param_idx}")
                    params.append(content)
                    param_idx += 1

                updates.append(f"version = version + 1")
                params.append(document_id)

                query = f"""
                    UPDATE documents
                    SET {', '.join(updates)}
                    WHERE id = ${param_idx}
                    RETURNING id, title, content, version, created_at, updated_at
                """

                row = await conn.fetchrow(query, *params)
                if row:
                    result = dict(row)
                    result["id"] = str(result["id"])
                    return result
                return None
        except Exception as e:
            raise DatabaseError(f"Failed to update document: {str(e)}") from e

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document.

        Args:
            document_id: Document UUID.

        Returns:
            True if deleted, False if not found.
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM documents WHERE id = $1",
                    document_id,
                )
                return result == "DELETE 1"
        except Exception as e:
            raise DatabaseError(f"Failed to delete document: {str(e)}") from e
