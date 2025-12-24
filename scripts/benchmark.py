"""Performance benchmarking script for RAG system."""

import asyncio
import time
from typing import List, Dict

import httpx


async def benchmark_query_service(
    base_url: str = "http://localhost:8003",
    num_queries: int = 100,
    concurrent: int = 10,
) -> Dict:
    """
    Benchmark the query service.

    Args:
        base_url: Base URL of query service.
        num_queries: Total number of queries to run.
        concurrent: Number of concurrent requests.

    Returns:
        Benchmark results.
    """
    queries = [
        "What is RAG?",
        "Explain vector databases",
        "How does change data capture work?",
        "What are embeddings?",
        "Describe machine learning",
    ] * (num_queries // 5 + 1)
    queries = queries[:num_queries]

    latencies = []
    errors = 0

    async def run_query(query: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                start = time.time()
                response = await client.post(
                    f"{base_url}/query",
                    json={"query": query},
                )
                latency = time.time() - start
                
                if response.status_code == 200:
                    data = response.json()
                    latencies.append(latency)
                else:
                    errors += 1
            except Exception as e:
                print(f"Error: {e}")
                errors += 1

    start_time = time.time()
    
    # Run queries in batches
    for i in range(0, len(queries), concurrent):
        batch = queries[i:i + concurrent]
        await asyncio.gather(*[run_query(q) for q in batch])

    total_time = time.time() - start_time

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        p50 = sorted(latencies)[len(latencies) // 2]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    else:
        avg_latency = p50 = p95 = p99 = 0

    return {
        "total_queries": num_queries,
        "successful": len(latencies),
        "errors": errors,
        "total_time_seconds": total_time,
        "queries_per_second": num_queries / total_time if total_time > 0 else 0,
        "avg_latency_seconds": avg_latency,
        "p50_latency_seconds": p50,
        "p95_latency_seconds": p95,
        "p99_latency_seconds": p99,
    }


async def benchmark_update_service(
    base_url: str = "http://localhost:8002",
    num_updates: int = 50,
) -> Dict:
    """
    Benchmark the update service processing.

    Args:
        base_url: Base URL of update service.
        num_updates: Number of test updates.

    Returns:
        Benchmark results.
    """
    # This would require inserting test documents and measuring processing time
    # For now, return a placeholder
    return {
        "note": "Update service benchmarking requires database setup",
        "num_updates": num_updates,
    }


if __name__ == "__main__":
    import json

    print("Running RAG system benchmarks...")
    
    query_results = asyncio.run(benchmark_query_service())
    print("\nQuery Service Results:")
    print(json.dumps(query_results, indent=2))
    
    update_results = asyncio.run(benchmark_update_service())
    print("\nUpdate Service Results:")
    print(json.dumps(update_results, indent=2))

