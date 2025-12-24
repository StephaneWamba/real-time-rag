"""Document chunking service."""

import uuid
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class ChunkingService:
    """Service for chunking documents into smaller pieces."""

    def __init__(self) -> None:
        """Initialize the chunking service."""
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )

    def _generate_chunk_uuid(self, document_id: str, chunk_index: int) -> str:
        """
        Generate a deterministic UUID for a chunk based on document_id and chunk_index.

        Args:
            document_id: ID of the source document.
            chunk_index: Index of the chunk.

        Returns:
            UUID string for the chunk.
        """
        namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
        name = f"{document_id}:{chunk_index}"
        return str(uuid.uuid5(namespace, name))

    def chunk_document(self, content: str, document_id: str) -> List[dict]:
        """
        Chunk a document into smaller pieces.

        Args:
            content: Document content to chunk.
            document_id: ID of the source document.

        Returns:
            List of chunk dictionaries with id, content, and metadata.
        """
        chunks = self.splitter.split_text(content)
        chunk_objects = []
        for idx, chunk_text in enumerate(chunks):
            chunk_id = self._generate_chunk_uuid(document_id, idx)
            chunk_objects.append(
                {
                    "id": chunk_id,
                    "content": chunk_text,
                    "chunk_index": idx,
                    "document_id": document_id,
                }
            )
        return chunk_objects
