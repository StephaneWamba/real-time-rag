"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str
    postgres_url: str = "postgresql://rag_user:rag_pass@postgres:5432/rag_db"
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_topic_documents: str = "documents.public.documents"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection_name: str = "documents"
    redis_url: str = "redis://redis:6379"
    service_name: str = "rag-service"
    service_port: int = 8000

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384
    llm_model: str = "gpt-4o-mini"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5

    cache_ttl: int = 3600

    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_multiplier: float = 2.0

    # Dead letter queue configuration
    dlq_topic: str = "documents.dlq"
    dlq_enabled: bool = True

    # Batch processing configuration
    batch_size: int = 10
    batch_timeout_seconds: float = 5.0

    # Connection pooling
    qdrant_pool_size: int = 10
    redis_pool_size: int = 10


settings = Settings()
