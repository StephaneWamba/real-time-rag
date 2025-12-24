# Real-Time RAG: Handling Live Data Updates Without Reindexing

**Complete Real-Time RAG system** with Change Data Capture (CDC), event-driven processing, incremental vector indexing, production monitoring, resilience features, and performance optimizations. Updates propagate from source database to vector search in **sub-second latency** without full reindexing.

> **Note**: This is a tutorial/blog project. Code can be refactored freely without backward compatibility concerns.

## Overview

Traditional RAG systems require full reindexing when documents change, causing downtime and high compute costs. This system implements real-time updates using CDC, Kafka event streaming, and incremental vector updates, maintaining sub-second update latency at scale.

## Architecture

```mermaid
graph TB
    subgraph "Source Layer"
        PG[(PostgreSQL<br/>Source Documents)]
    end

    subgraph "CDC Layer"
        DEB[Debezium<br/>Change Capture]
    end

    subgraph "Event Streaming"
        ZK[Zookeeper]
        KAFKA[Kafka<br/>Event Broker]
    end

    subgraph "Processing Layer"
        UPDATE[Update Service<br/>Incremental Indexing]
    end

    subgraph "Query Layer"
        QUERY[Query Service<br/>RAG Endpoint]
    end

    subgraph "Storage Layer"
        QDRANT[(Qdrant<br/>Vector DB)]
        REDIS[(Redis<br/>Cache)]
    end

    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
    end

    PG -->|CDC| DEB
    DEB -->|Events| KAFKA
    KAFKA -->|Consume| UPDATE
    UPDATE -->|Upsert| QDRANT
    UPDATE -->|Metrics| PROM
    QUERY -->|Search| QDRANT
    QUERY -->|Cache| REDIS
    QUERY -->|Metrics| PROM
    PROM -->|Visualize| GRAF
    ZK -->|Coordination| KAFKA
```

## Key Features

### Core RAG Capabilities

- **Change Data Capture**: Debezium captures PostgreSQL changes in real-time
- **Event-Driven Updates**: Kafka streams document changes to processing services
- **Incremental Indexing**: Only changed chunks are re-embedded and updated
- **Version Tracking**: Document versions prevent stale data in queries
- **Idempotent Processing**: Duplicate events handled safely
- **Sub-Second Latency**: Updates propagate in <1 second under normal load

### Production Enhancements

- **Health Checks**: Dependency verification for all services
- **Retry Logic**: Exponential backoff for failed operations
- **Dead Letter Queue**: Failed events captured for analysis
- **Batch Processing**: High-volume update optimization
- **Query Pagination**: Paginated source results
- **Multi-Collection Support**: Multiple vector collections
- **Monitoring**: Prometheus metrics + Grafana dashboards
- **Alerting**: Automated alerts for lag, errors, and downtime
- **Performance Benchmarking**: Load testing tools
- **Observability**: Prometheus metrics and Grafana dashboards for update lag, throughput, failures

## Tech Stack

| Component           | Technology                      | Purpose                  |
| ------------------- | ------------------------------- | ------------------------ |
| **Source DB**       | PostgreSQL                      | Document source of truth |
| **CDC**             | Debezium                        | Real-time change capture |
| **Event Streaming** | Apache Kafka + Zookeeper        | Event distribution       |
| **Vector DB**       | Qdrant                          | Semantic search          |
| **Cache**           | Redis                           | Query result caching     |
| **Update Service**  | FastAPI + Python                | Incremental indexing     |
| **Query Service**   | FastAPI + Python                | RAG endpoint             |
| **Embeddings**      | OpenAI `text-embedding-3-small` | Vector generation        |
| **LLM**             | OpenAI `gpt-4o-mini`            | Response generation      |
| **Monitoring**      | Prometheus + Grafana            | Metrics and dashboards   |

## Prerequisites

- Docker and Docker Compose
- OpenAI API key
- 8GB+ RAM (for Kafka, PostgreSQL, Qdrant)
- Python 3.11+

## Quick Start

### 1. Clone and Setup

```bash
cd tutorials/real-time-rag

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

### 2. Start Services

```bash
docker compose up -d
```

This starts:

- PostgreSQL (source database)
- Zookeeper + Kafka (event streaming)
- Debezium (CDC connector)
- Qdrant (vector database)
- Redis (caching)
- Update Service (incremental indexing)
- Query Service (RAG endpoint)
- Prometheus + Grafana (monitoring)

### 3. Configure Debezium Connector

Wait for all services to be healthy, then configure the Debezium connector:

```bash
curl -X POST http://localhost:8084/connectors \
  -H "Content-Type: application/json" \
  -d @debezium/connector-config.json
```

### 4. Ingest Initial Data

```bash
docker compose exec update-service python scripts/ingest_initial.py
```

### 5. Test Real-Time Updates

```bash
# Update a document in PostgreSQL
docker compose exec postgres psql -U rag_user -d rag_db \
  -c "UPDATE documents SET content = 'Updated content', version = version + 1 WHERE id = 'doc-1';"

# Query immediately - should reflect update within seconds
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{"query": "your question"}'
```

## Project Structure

```
real-time-rag/
├── app/
│   ├── api/
│   │   └── health.py              # Health check utilities
│   ├── core/
│   │   ├── config.py              # Application configuration
│   │   ├── dependencies.py        # Service container & DI
│   │   └── exceptions.py          # Custom exceptions
│   ├── models/
│   │   ├── document.py            # Document models
│   │   ├── document_api.py        # API request/response models
│   │   ├── event.py               # Kafka event models
│   │   └── response.py            # Query response models
│   ├── monitoring/
│   │   └── metrics.py             # Prometheus metrics
│   ├── services/
│   │   ├── batch.py               # Batch processing utility
│   │   ├── cache.py               # Redis caching service
│   │   ├── chunking.py            # Document chunking (deterministic)
│   │   ├── database.py            # PostgreSQL operations
│   │   ├── dlq.py                 # Dead letter queue service
│   │   ├── embedding.py           # OpenAI embedding generation
│   │   ├── event_processor.py     # Event processing logic
│   │   ├── health.py              # Health check service
│   │   ├── llm.py                 # LLM service (structured responses)
│   │   ├── metrics_parser.py      # Prometheus metrics parser
│   │   ├── metrics_tracker.py     # In-memory metrics tracker
│   │   ├── pipeline_tracker.py   # Pipeline latency tracking
│   │   ├── query_processor.py     # Query processing logic
│   │   ├── retry.py               # Retry with exponential backoff
│   │   └── vector_db.py           # Qdrant operations
│   ├── update_service.py        # Update service (Kafka consumer + API)
│   └── query_service.py          # Query service (RAG endpoint)
├── scripts/
│   ├── benchmark.py               # Performance benchmarking
│   ├── ingest_initial.py          # Initial data ingestion
│   └── setup_debezium.ps1        # Debezium connector setup (PowerShell)
├── debezium/
│   ├── connector-config.json      # Debezium connector configuration
│   └── connector-config-only.json # Connector config (no wrapper)
├── docker/
│   ├── postgres/
│   │   └── init.sql               # Database schema & WAL config
│   └── prometheus/
│       └── prometheus.yml         # Prometheus configuration
├── frontend/                      # React frontend UI
│   ├── src/
│   │   ├── components/           # UI components (Document, Pipeline, Query, Metrics)
│   │   ├── services/             # API client
│   │   └── App.tsx               # Main app component
│   └── README.md                 # Frontend setup instructions
├── grafana/
│   └── dashboards/
│       └── rag-metrics.json      # Grafana dashboard definition
├── prometheus/
│   └── alerts.yml                 # Prometheus alert rules
├── docker-compose.yml             # Service orchestration
├── Dockerfile                     # Python service container
├── pyproject.toml                 # Python dependencies
├── .env.example                   # Environment variables template
├── README.md                      # This file
└── docs/                          # Documentation
    ├── architecture.md            # System architecture and data flows
    ├── production.md              # Production features and enhancements
    └── guides.md                  # Setup, deployment, troubleshooting
```

## How It Works

### Update Flow

1. **Document Change**: Update occurs in PostgreSQL
2. **CDC Capture**: Debezium captures the change event
3. **Event Streaming**: Kafka receives and distributes the event
4. **Processing**: Update Service consumes event, chunks document, generates embeddings
5. **Vector Update**: Only changed chunks are upserted to Qdrant
6. **Consistency**: Query Service uses version tracking to ensure fresh data

### Query Flow

1. **Query Received**: Query Service receives user query
2. **Cache Check**: Check Redis for cached response
3. **Embedding**: Generate query embedding if not cached
4. **Vector Search**: Search Qdrant for relevant chunks
5. **LLM Generation**: Generate answer using retrieved context
6. **Cache Update**: Store response and embeddings in Redis

## API Endpoints

### Query Service (`http://localhost:8003`)

- `POST /query` - RAG query with pagination
  ```json
  {
    "query": "Your question here",
    "page": 1,
    "page_size": 10
  }
  ```
- `GET /health` - Health check with dependency status
- `GET /ready` - Readiness probe (Kubernetes)
- `GET /collections` - List all Qdrant collections
- `GET /metrics` - Prometheus metrics (JSON format)

### Update Service (`http://localhost:8002`)

- `GET /health` - Health check with dependency status
- `GET /ready` - Readiness probe (Kubernetes)
- `GET /api/documents` - List documents (with pagination)
- `GET /api/documents/{id}` - Get document by ID
- `POST /api/documents` - Create new document
- `PUT /api/documents/{id}` - Update document
- `DELETE /api/documents/{id}` - Delete document
- `GET /api/pipeline/status` - Get pipeline latency status
- `GET /api/metrics` - Prometheus metrics (JSON format)

## Monitoring

### Metrics

- **Update Lag**: Time from DB change to vector update (target: <1s)
- **Throughput**: Updates processed per second
- **Failed Updates**: Count of failed processing attempts
- **Query Latency**: End-to-end query response time
- **Cache Hit Rate**: Percentage of queries served from cache

### Dashboards

Access Grafana at `http://localhost:3002` (default password: `admin`):

- Update pipeline health
- Query performance
- Error rates and retries
- System resource usage

Import the dashboard from `grafana/dashboards/rag-metrics.json` or it will be auto-provisioned.

### Prometheus

Access Prometheus at `http://localhost:9091`:

- Query metrics: `update_lag_seconds`, `query_latency_seconds`, `updates_total`, etc.
- View alerts: Configured in `prometheus/alerts.yml`

## Port Mappings

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

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

Key environment variables (see `.env.example` for all options):

- **OPENAI_API_KEY** (required): Your OpenAI API key for embeddings and LLM
- **POSTGRES_URL**: PostgreSQL connection string (default: `postgresql://rag_user:rag_pass@postgres:5432/rag_db`)
- **KAFKA_BOOTSTRAP_SERVERS**: Kafka broker address (default: `kafka:29092`)
- **QDRANT_URL**: Qdrant vector database URL (default: `http://qdrant:6333`)
- **REDIS_URL**: Redis cache URL (default: `redis://redis:6379`)

All configuration options are documented in `app/core/config.py` with sensible defaults.

## Production Considerations

- **Idempotency**: Event processing is idempotent (safe to replay)
- **Backpressure**: Update Service handles Kafka lag gracefully
- **Failure Recovery**: Failed updates are retried with exponential backoff
- **Versioning**: Document versions prevent race conditions
- **Scaling**: Update and Query services can be horizontally scaled
- **Monitoring**: Comprehensive metrics for production debugging

## Frontend UI

A minimalist React frontend is included to demonstrate the system capabilities:

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

# Run performance benchmark
docker compose exec query-service python scripts/benchmark.py
```

## Troubleshooting

### Debezium Connection Issues

If Debezium fails to connect:

1. Verify PostgreSQL `wal_level = logical` (check `docker/postgres/init.sql`)
2. Ensure Debezium user has `REPLICATION` privilege
3. Check Debezium logs: `docker compose logs debezium`

### Replication Slot Growth

Monitor slot lag:

```sql
SELECT slot_name, pg_size_pretty(pg_wal_lsn_diff(
  pg_current_wal_lsn(), confirmed_flush_lsn
)) AS lag FROM pg_replication_slots;
```

If lag exceeds 1GB, investigate consumer performance or consider `max_slot_wal_keep_size`.

### Kafka Consumer Lag

Check consumer lag:

```bash
docker compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group update-service --describe
```

Scale horizontally by adding more update-service instances.

## Limitations

- Requires PostgreSQL as source database (Debezium limitation)
- Kafka requires persistent storage for event retention
- Update latency depends on embedding API response time
- Large batch updates may cause temporary lag

## Additional Documentation

- **[docs/architecture.md](docs/architecture.md)**: How the system works - architecture and data flows
- **[docs/production.md](docs/production.md)**: Production features and enhancements
- **[docs/guides.md](docs/guides.md)**: Setup, deployment, and troubleshooting
- **[frontend/README.md](frontend/README.md)**: Frontend setup and usage

## License

MIT
