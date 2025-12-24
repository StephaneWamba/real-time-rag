"""Custom exceptions for the application."""


class VectorDBError(Exception):
    """Raised when vector database operations fail."""

    pass


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class LLMError(Exception):
    """Raised when LLM operations fail."""

    pass


class CacheError(Exception):
    """Raised when cache operations fail."""

    pass


class KafkaError(Exception):
    """Raised when Kafka operations fail."""

    pass


class DLQError(Exception):
    """Raised when Dead Letter Queue operations fail."""

    pass


class DatabaseError(Exception):
    """Raised when database operations fail."""

    pass

