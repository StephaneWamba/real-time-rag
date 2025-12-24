FROM python:3.11-slim

WORKDIR /app

# Install uv in a single layer
RUN pip install --no-cache-dir uv

# Copy dependency file first for better layer caching
# Dependencies are installed in a separate layer so code changes don't invalidate dependency cache
COPY pyproject.toml ./

# Install all dependencies in one layer (keeps dependency layer separate from code)
RUN uv pip install --system --no-cache \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    openai>=1.3.0 \
    instructor>=1.0.0 \
    qdrant-client>=1.7.0 \
    redis>=5.0.0 \
    aiokafka>=0.10.0 \
    asyncpg>=0.29.0 \
    httpx>=0.25.0 \
    prometheus-client>=0.19.0 \
    python-multipart>=0.0.6 \
    tiktoken>=0.5.0 \
    langchain-text-splitters>=0.0.1

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy application code last (this layer changes most frequently)
# This ensures dependency layer is cached when only code changes
COPY app/ ./app/

# Change ownership and switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Default command (overridden by docker-compose for each service)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

