# Setup, Deployment & Troubleshooting

Complete guide to setting up, deploying, and troubleshooting the Real-Time RAG system.

## Prerequisites

Before you begin, ensure you have:

- **Docker and Docker Compose**: For running all services
- **OpenAI API Key**: For embeddings and LLM generation
- **8GB+ RAM**: Required for Kafka, PostgreSQL, and Qdrant
- **Python 3.11+**: For running scripts (if needed)

## Quick Start

### 1. Clone and Setup

```bash
cd tutorials/real-time-rag

# Create .env file with your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Start Services

```bash
docker compose up -d
```

This starts all services:

- PostgreSQL (source database)
- Zookeeper + Kafka (event streaming)
- Debezium (CDC connector)
- Qdrant (vector database)
- Redis (caching)
- Update Service (incremental indexing)
- Query Service (RAG endpoint)
- Prometheus + Grafana (monitoring)

Wait for all services to be healthy (check with `docker compose ps`).

### 3. Configure Debezium Connector

Configure the Debezium connector to start capturing changes:

```bash
curl -X POST http://localhost:8084/connectors \
  -H "Content-Type: application/json" \
  -d @debezium/connector-config.json
```

Verify the connector is running:

```bash
curl http://localhost:8084/connectors/documents-connector/status
```

### 4. Ingest Initial Data

Ingest some initial documents to test the system:

```bash
docker compose exec update-service python scripts/ingest_initial.py
```

This creates sample documents in PostgreSQL, which will be automatically indexed by the Update Service.

### 5. Test Real-Time Updates

Update a document and verify it's reflected in queries:

```bash
# Update a document in PostgreSQL
docker compose exec postgres psql -U rag_user -d rag_db \
  -c "UPDATE documents SET content = 'Updated content', version = version + 1 WHERE id = 'doc-1';"

# Query immediately - should reflect update within seconds
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{"query": "your question"}'
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key environment variables:

- **OPENAI_API_KEY** (required): Your OpenAI API key for embeddings and LLM
- **POSTGRES_URL**: PostgreSQL connection string (default: `postgresql://rag_user:rag_pass@postgres:5432/rag_db`)
- **KAFKA_BOOTSTRAP_SERVERS**: Kafka broker address (default: `kafka:29092`)
- **QDRANT_URL**: Qdrant vector database URL (default: `http://qdrant:6333`)
- **REDIS_URL**: Redis cache URL (default: `redis://redis:6379`)

All configuration options are documented in `app/core/config.py` with sensible defaults.

### Port Mappings

| Service        | External Port | Internal Port | URL                           |
| -------------- | ------------- | ------------- | ----------------------------- |
| PostgreSQL     | 5434          | 5432          | `postgresql://localhost:5434` |
| Zookeeper      | 2182          | 2181          | `localhost:2182`              |
| Kafka          | 9094          | 9092          | `localhost:9094`              |
| Debezium       | 8084          | 8083          | `http://localhost:8084`       |
| Qdrant         | 6335          | 6333          | `http://localhost:6335`       |
| Redis          | 6381          | 6379          | `redis://localhost:6381`      |
| Update Service | 8002          | 8001          | `http://localhost:8002`       |
| Query Service  | 8003          | 8000          | `http://localhost:8003`       |
| Prometheus     | 9091          | 9090          | `http://localhost:9091`       |
| Grafana        | 3002          | 3000          | `http://localhost:3002`       |

## API Endpoints

### Query Service (`http://localhost:8003`)

- **`POST /query`**: RAG query with pagination
  ```json
  {
    "query": "Your question here",
    "page": 1,
    "page_size": 10
  }
  ```
- **`GET /health`**: Health check with dependency status
- **`GET /ready`**: Readiness probe (Kubernetes)
- **`GET /collections`**: List all Qdrant collections
- **`GET /api/metrics`**: Prometheus metrics (JSON format)

### Update Service (`http://localhost:8002`)

- **`GET /health`**: Health check with dependency status
- **`GET /ready`**: Readiness probe (Kubernetes)
- **`GET /api/documents`**: List documents (with pagination)
- **`GET /api/documents/{id}`**: Get document by ID
- **`POST /api/documents`**: Create new document
- **`PUT /api/documents/{id}`**: Update document
- **`DELETE /api/documents/{id}`**: Delete document
- **`GET /api/pipeline/status`**: Get pipeline latency status
- **`GET /api/metrics`**: Prometheus metrics (JSON format)

## Development

### Running Services Locally

Services run in Docker containers with hot-reload enabled for development:

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f update-service
docker compose logs -f query-service

# Restart a service
docker compose restart update-service
```

### Running Scripts

```bash
# Ingest initial documents
docker compose exec update-service python scripts/ingest_initial.py

```

### Frontend UI

A minimalist React frontend is included to demonstrate the system:

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend provides:

- **Document Management**: Create, edit, view, and delete documents
- **Pipeline Visualization**: Real-time update pipeline flow with stage latencies
- **Query Interface**: Submit RAG queries and view responses with citations
- **Metrics Dashboard**: Monitor update lag and query latency with charts

See `frontend/README.md` for detailed setup instructions.

## Troubleshooting

### Debezium Connection Issues

**Symptoms**: Debezium connector fails to start or connect to PostgreSQL.

**Solutions**:

1. Verify PostgreSQL `wal_level = logical`:
   ```sql
   SHOW wal_level;
   ```
   If not `logical`, check `docker/postgres/init.sql` and restart PostgreSQL.

2. Ensure Debezium user has `REPLICATION` privilege:
   ```sql
   SELECT rolreplication FROM pg_roles WHERE rolname = 'rag_user';
   ```

3. Check Debezium logs:
   ```bash
   docker compose logs debezium
   ```

4. Verify connector status:
   ```bash
   curl http://localhost:8084/connectors/documents-connector/status
   ```

### Replication Slot Growth

**Symptoms**: WAL lag increasing, disk usage growing.

**Check Lag**:
```sql
SELECT slot_name, pg_size_pretty(pg_wal_lsn_diff(
  pg_current_wal_lsn(), confirmed_flush_lsn
)) AS lag FROM pg_replication_slots;
```

**Solutions**:

- Investigate consumer performance (check Update Service logs)
- Consider `max_slot_wal_keep_size` setting in PostgreSQL
- Scale update service horizontally to process events faster
- Monitor Prometheus metrics for update lag

### Kafka Consumer Lag

**Symptoms**: Updates delayed, consumer lag increasing.

**Check Lag**:
```bash
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group update-service --describe
```

**Solutions**:

- Scale update service horizontally (add more instances)
- Increase Kafka partitions for better parallelism
- Check processing performance (embedding API latency, Qdrant performance)
- Monitor Prometheus metrics for throughput

### Qdrant Connection Errors

**Symptoms**: Vector operations failing, "connection refused" errors.

**Solutions**:

1. Verify Qdrant is running:
   ```bash
   docker compose ps qdrant
   ```

2. Check Qdrant logs:
   ```bash
   docker compose logs qdrant
   ```

3. Verify collection exists:
   ```bash
   curl http://localhost:6335/collections
   ```

4. Test connection:
   ```bash
   curl http://localhost:6335/health
   ```

### Redis Connection Errors

**Symptoms**: Cache operations failing, "connection refused" errors.

**Solutions**:

1. Verify Redis is running:
   ```bash
   docker compose ps redis
   ```

2. Test connection:
   ```bash
   docker compose exec redis redis-cli ping
   ```

3. Check Redis logs:
   ```bash
   docker compose logs redis
   ```

### High Update Latency

**Symptoms**: Updates taking >3 seconds.

**Check**:

- Embedding API latency (OpenAI response time)
- Qdrant upsert performance
- Kafka consumer lag
- Network latency between services

**Solutions**:

- Monitor Prometheus metrics (`update_lag_seconds`)
- Check OpenAI API rate limits and status
- Scale update service horizontally
- Optimize chunking strategy (reduce chunk size if needed)

### Query Timeouts

**Symptoms**: Queries timing out or slow responses.

**Check**:

- Query latency metrics (`query_latency_seconds`)
- Cache hit rate (should be >50% for repeated queries)
- LLM API latency (OpenAI response time)
- Qdrant search performance

**Solutions**:

- Increase cache TTL to improve hit rate
- Optimize source filtering (reduce `TOP_K` if needed)
- Check OpenAI API status and rate limits
- Scale query service horizontally

### Service Health Checks Failing

**Symptoms**: `/health` endpoint returns `unhealthy` status.

**Solutions**:

1. Check individual dependency status in the health response
2. Verify all services are running: `docker compose ps`
3. Check service logs for connection errors
4. Verify environment variables are set correctly
5. Test connectivity manually (e.g., `curl http://localhost:6335/health`)

## Monitoring

### Prometheus

Access Prometheus at `http://localhost:9091`:

- Query metrics: `update_lag_seconds`, `query_latency_seconds`, `updates_total`, etc.
- View alerts: Configured in `prometheus/alerts.yml`

### Grafana

Access Grafana at `http://localhost:3002` (default password: `admin`):

- Import dashboard from `grafana/dashboards/rag-metrics.json`
- View update pipeline health
- Monitor query performance
- Track error rates and retries

### Key Metrics to Monitor

- **Update Lag**: Should be <1 second under normal load
- **Query Latency**: Should be <2 seconds for cached queries
- **Cache Hit Rate**: Should be >50% for repeated queries
- **Error Rate**: Should be <1% of total operations
- **Consumer Lag**: Should be <1000 messages

## Limitations

- **PostgreSQL Required**: Debezium only supports PostgreSQL as source database
- **Kafka Storage**: Kafka requires persistent storage for event retention
- **Embedding API Latency**: Update latency depends on OpenAI API response time
- **Batch Updates**: Large batch updates may cause temporary lag

## Additional Resources

- **Architecture**: See [docs/architecture.md](architecture.md) for detailed system design
- **Production Features**: See [docs/production.md](production.md) for production enhancements
- **Frontend**: See `frontend/README.md` for frontend setup instructions

