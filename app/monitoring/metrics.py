"""Prometheus metrics for monitoring."""

from prometheus_client import Counter, Histogram

query_counter = Counter("rag_queries_total",
                        "Total number of queries processed")
query_errors_total = Counter(
    "rag_query_errors_total", "Total number of query errors")
query_latency_seconds = Histogram(
    "rag_query_latency_seconds", "Query latency in seconds", buckets=[0.1, 0.5, 1.0, 2.0, 5.0])
query_duration_seconds = Histogram(
    "rag_query_duration_seconds", "Query processing duration", buckets=[0.1, 0.5, 1.0, 2.0, 5.0])

updates_total = Counter("rag_updates_total",
                        "Total number of document updates processed")
update_errors_total = Counter(
    "rag_update_errors_total", "Total number of update errors")
update_lag_seconds = Histogram("rag_update_lag_seconds", "Time from DB change to vector update", buckets=[
                               0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
update_processing_duration = Histogram(
    "rag_update_processing_duration_seconds", "Update processing duration", buckets=[0.1, 0.5, 1.0, 2.0, 5.0])


