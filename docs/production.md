# Production Features & Enhancements

This guide covers the production-ready features that make the Real-Time RAG system resilient, observable, and performant.

## Health Checks

Both services expose health check endpoints that verify all dependencies:

### Endpoints

- **`GET /health`**: Comprehensive health check with dependency status
- **`GET /ready`**: Readiness probe for Kubernetes (simpler check)

### Dependencies Checked

- **Qdrant**: Vector database connectivity
- **Redis**: Cache connectivity
- **OpenAI**: API key validity and connectivity
- **Kafka**: Broker connectivity
- **PostgreSQL**: Database connectivity

### Example Response

```json
{
  "status": "healthy",
  "dependencies": {
    "qdrant": { "status": "healthy", "latency_ms": 5 },
    "redis": { "status": "healthy", "latency_ms": 2 },
    "openai": { "status": "healthy", "latency_ms": 120 },
    "kafka": { "status": "healthy", "latency_ms": 10 },
    "postgres": { "status": "healthy", "latency_ms": 3 }
  }
}
```

Use these endpoints for load balancer health checks and Kubernetes readiness/liveness probes.

## Retry Logic

Transient failures (network issues, API rate limits) are automatically retried with exponential backoff.

### How It Works

- **Exponential Backoff**: Delays increase exponentially (1s, 2s, 4s, ...)
- **Configurable Retries**: Maximum retry attempts (default: 3)
- **Applied To**: Embedding generation, vector DB operations, LLM calls

### Configuration

Set these environment variables to customize retry behavior:

```bash
MAX_RETRIES=3                    # Maximum retry attempts
RETRY_DELAY_SECONDS=1.0         # Initial delay in seconds
RETRY_BACKOFF_MULTIPLIER=2.0   # Backoff multiplier
```

### When Retries Happen

- OpenAI API rate limits or temporary failures
- Qdrant connection timeouts
- Network interruptions
- Transient database errors

After max retries, the event is sent to the Dead Letter Queue (if enabled).

## Dead Letter Queue (DLQ)

Failed events that cannot be processed after retries are captured in a Dead Letter Queue for analysis and manual reprocessing.

### How It Works

- **Failed Events**: Events that fail after all retries are sent to a Kafka DLQ topic
- **Preserved Data**: Original event data, error message, and metadata are preserved
- **Manual Reprocessing**: Events can be manually replayed from the DLQ topic

### Configuration

```bash
DLQ_ENABLED=true                # Enable/disable DLQ
DLQ_TOPIC=documents.dlq        # Kafka topic for failed events
```

### DLQ Event Format

```json
{
  "original_event": { ... },
  "error_message": "Failed to generate embeddings: Rate limit exceeded",
  "timestamp": "2025-12-24T10:00:00Z",
  "retry_count": 3
}
```

Use the DLQ to identify patterns in failures and improve error handling.

## Batch Processing

High-volume updates can be processed in batches for better throughput and resource utilization.

### How It Works

- **Batch Buffer**: Events are collected in a buffer
- **Automatic Processing**: Batches are processed when the buffer is full or a timeout is reached
- **Thread-Safe**: Multiple threads can safely add items to the batch

### Configuration

```bash
BATCH_SIZE=10                   # Items per batch
BATCH_TIMEOUT_SECONDS=5.0       # Max wait time before processing
```

### When to Use

- High-volume document updates
- Bulk document ingestion
- Performance optimization for embedding generation

## Connection Pooling

Database and cache connections are pooled to improve performance and resource utilization.

### Qdrant

- Client timeout configuration prevents hanging connections
- Connection reuse reduces overhead

### Redis

- Connection pool with configurable size
- Reuses connections across requests

### Configuration

```bash
QDRANT_POOL_SIZE=10            # Qdrant connection pool size
REDIS_POOL_SIZE=10             # Redis connection pool size
```

## Query Result Caching

Query results and embeddings are cached in Redis to reduce latency and API costs.

### How It Works

- **TTL-Based Expiration**: Cached results expire after a configurable time
- **Cache Versioning**: Cache keys include version numbers to invalidate old entries
- **Embedding Caching**: Query embeddings are cached separately for reuse

### Configuration

```bash
CACHE_TTL=3600                 # Cache TTL in seconds (default: 1 hour)
```

### Cache Strategy

- **Query Results**: Full query responses cached with TTL
- **Query Embeddings**: Query embeddings cached separately
- **Versioning**: Cache keys include version to handle schema changes

## Monitoring & Observability

Comprehensive metrics are collected using Prometheus and visualized in Grafana.

### Key Metrics

- **Update Lag**: Time from DB change to vector update (target: <1s)
- **Throughput**: Updates processed per second
- **Failed Updates**: Count of failed processing attempts
- **Query Latency**: End-to-end query response time
- **Cache Hit Rate**: Percentage of queries served from cache

### Accessing Metrics

- **Prometheus**: `http://localhost:9091` - Query raw metrics
- **Grafana**: `http://localhost:3002` - Visualize metrics in dashboards
- **JSON Endpoints**: `GET /api/metrics` - Get metrics in JSON format

### Grafana Dashboards

Pre-configured dashboards show:

- Update pipeline health and latency
- Query performance and cache hit rates
- Error rates and retry counts
- System resource usage

Import the dashboard from `grafana/dashboards/rag-metrics.json` or it will be auto-provisioned.

### Alerting

Prometheus alert rules are configured in `prometheus/alerts.yml`:

- High update lag (>5 seconds)
- High error rate (>10% failures)
- Service downtime
- Consumer lag warnings

## Performance Optimizations

### Source Filtering

Low-confidence sources are filtered out before sending to the LLM, improving answer quality and reducing costs.

### Context Truncation

Context is truncated to fit within LLM token limits, preventing errors and reducing API costs.

### Query Pagination

Large result sets are paginated to improve response times and reduce memory usage.

### Multi-Collection Support

Multiple Qdrant collections can be used to organize documents by type, domain, or tenant.

## Production Considerations

### Idempotency

Event processing is idempotent, meaning events can be safely replayed without causing duplicates. This is achieved through:

- Deterministic chunking (same content = same chunk IDs)
- Version tracking (updates replace old chunks)
- Idempotent vector upserts

### Backpressure

The Update Service handles Kafka lag gracefully by:

- Processing events as fast as possible
- Monitoring consumer lag
- Scaling horizontally when needed

### Failure Recovery

- **Retry Logic**: Automatic retries with exponential backoff
- **Dead Letter Queue**: Failed events captured for analysis
- **Health Checks**: Dependency status monitored continuously

### Scaling

Both Update and Query services can be horizontally scaled:

- **Update Service**: Scale to handle high update volumes
- **Query Service**: Scale to handle high query volumes
- **Kafka Partitions**: Increase partitions to parallelize processing

### Versioning

Document versions prevent race conditions and ensure queries always return fresh data. Old chunks are filtered out automatically, not deleted immediately, allowing for safe rollbacks.

