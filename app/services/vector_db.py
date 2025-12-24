"""Qdrant vector database service."""

from typing import List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, NearestQuery, PointStruct, VectorParams

from app.core.config import settings
from app.core.exceptions import VectorDBError


class VectorDBService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self) -> None:
        """Initialize the vector database service."""
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = settings.qdrant_collection_name
        self.dimensions = settings.embedding_dimensions

    async def connect(self) -> None:
        """Connect to Qdrant."""
        try:
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                timeout=30.0,
            )
            await self._ensure_collection()
        except Exception as e:
            raise VectorDBError(
                f"Failed to connect to Qdrant: {str(e)}") from e

    async def disconnect(self) -> None:
        """Disconnect from Qdrant."""
        if self.client:
            await self.client.close()

    async def _ensure_collection(self) -> None:
        """Ensure the collection exists."""
        if not self.client:
            raise VectorDBError("Client not connected")

        collections = await self.client.get_collections()
        collection_names = [col.name for col in collections.collections]

        if self.collection_name not in collection_names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimensions,
                    distance=Distance.COSINE,
                ),
            )

    async def list_collections(self) -> List[str]:
        """
        List all available collections.

        Returns:
            List of collection names.
        """
        if not self.client:
            raise VectorDBError("Client not connected")

        collections = await self.client.get_collections()
        return [col.name for col in collections.collections]

    async def create_collection(self, collection_name: str) -> None:
        """
        Create a new collection.

        Args:
            collection_name: Name of the collection to create.
        """
        if not self.client:
            raise VectorDBError("Client not connected")

        collections = await self.client.get_collections()
        collection_names = [col.name for col in collections.collections]

        if collection_name in collection_names:
            raise VectorDBError(f"Collection {collection_name} already exists")

        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=self.dimensions,
                distance=Distance.COSINE,
            ),
        )

    async def upsert_chunks(
        self, chunks: List[dict], embeddings: List[List[float]], document_id: str, version: int
    ) -> None:
        """
        Upsert document chunks into the vector database.

        Args:
            chunks: List of chunk dictionaries.
            embeddings: List of embedding vectors.
            document_id: ID of the source document.
            version: Document version number.
        """
        if not self.client:
            raise VectorDBError("Client not connected")

        if len(chunks) != len(embeddings):
            raise VectorDBError(
                "Chunks and embeddings must have the same length")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=chunk["id"],
                    vector=embedding,
                    payload={
                        "document_id": document_id,
                        "content": chunk["content"],
                        "chunk_index": chunk["chunk_index"],
                        "version": version,
                    },
                )
            )

        await self.client.upsert(collection_name=self.collection_name, points=points)

    async def delete_document_chunks(self, document_id: str) -> None:
        """
        Delete all chunks for a document.

        Args:
            document_id: ID of the document to delete.
        """
        if not self.client:
            raise VectorDBError("Client not connected")

        await self.client.delete(
            collection_name=self.collection_name,
            points_selector={"filter": {
                "must": [{"key": "document_id", "match": {"value": document_id}}]}},
        )

    async def search(
        self, query_embedding: List[float], top_k: int = 5, min_version: Optional[int] = None
    ) -> List[dict]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query embedding vector.
            top_k: Number of results to return.
            min_version: Minimum document version to consider.

        Returns:
            List of matching chunks with scores.
        """
        if not self.client:
            raise VectorDBError("Client not connected")

        query_filter = None
        if min_version is not None:
            query_filter = {
                "must": [{"key": "version", "range": {"gte": min_version}}]}

        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=NearestQuery(nearest=query_embedding),
            limit=top_k,
            query_filter=query_filter,
        )

        matches = []
        for point in results.points:
            matches.append(
                {
                    "id": str(point.id),
                    "content": point.payload.get("content", ""),
                    "document_id": point.payload.get("document_id"),
                    "score": point.score,
                    "version": point.payload.get("version", 1),
                }
            )

        return matches
