# Real-Time RAG Frontend

Minimalist UI for demonstrating Real-Time RAG system capabilities.

## Features

- **Document Management**: Create, edit, and view documents
- **Pipeline Visualization**: Real-time update pipeline flow
- **Query Interface**: Ask questions and get RAG responses
- **Metrics Dashboard**: Monitor update lag and query latency

## Setup

```bash
pnpm install
pnpm dev
```

## Environment Variables

Create a `.env` file:

```
VITE_API_URL=http://localhost:8003
VITE_UPDATE_API_URL=http://localhost:8002
```

## Tech Stack

- React 19 + TypeScript
- Vite
- Recharts (for metrics)
- Axios (for API calls)
- Minimalist CSS (no UI framework)
