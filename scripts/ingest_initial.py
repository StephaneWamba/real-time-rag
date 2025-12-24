"""Script to ingest initial documents into PostgreSQL."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


async def ingest_sample_documents() -> None:
    """Ingest sample documents into PostgreSQL."""
    conn = await asyncpg.connect(settings.postgres_url)

    sample_documents = [
        {
            "id": uuid4(),
            "title": "Introduction to RAG Systems",
            "content": "Retrieval-Augmented Generation (RAG) combines the power of information retrieval with language models. "
            "It allows systems to access external knowledge bases and provide accurate, up-to-date answers. "
            "RAG systems typically consist of a retriever that finds relevant documents and a generator that creates responses.",
        },
        {
            "id": uuid4(),
            "title": "Change Data Capture Overview",
            "content": "Change Data Capture (CDC) is a technique for identifying and capturing changes made to data in a database. "
            "CDC enables real-time data synchronization by tracking INSERT, UPDATE, and DELETE operations. "
            "Common CDC tools include Debezium, which captures changes from database transaction logs.",
        },
        {
            "id": uuid4(),
            "title": "Vector Databases for Semantic Search",
            "content": "Vector databases store high-dimensional vectors and enable fast similarity search. "
            "They are essential for RAG systems as they allow efficient retrieval of semantically similar documents. "
            "Popular vector databases include Qdrant, Pinecone, and Weaviate. They use algorithms like HNSW for fast approximate nearest neighbor search.",
        },
    ]

    for doc in sample_documents:
        await conn.execute(
            """
            INSERT INTO documents (id, title, content, version)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (id) DO NOTHING
            """,
            doc["id"],
            doc["title"],
            doc["content"],
        )
        print(f"Inserted document: {doc['title']}")

    await conn.close()
    print(f"\nIngested {len(sample_documents)} documents")


if __name__ == "__main__":
    asyncio.run(ingest_sample_documents())




