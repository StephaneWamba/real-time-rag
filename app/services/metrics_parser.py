"""Parse Prometheus metrics for API responses."""

import re
from typing import Dict, List, Optional
from prometheus_client import generate_latest, REGISTRY


def parse_prometheus_metrics() -> Dict[str, any]:
    """
    Parse Prometheus metrics and return structured data.

    Returns:
        Dictionary with parsed metrics.
    """
    metrics_text = generate_latest(REGISTRY).decode('utf-8')
    metrics = {}

    for line in metrics_text.split('\n'):
        if not line or line.startswith('#'):
            continue

        # Parse metric line: metric_name{labels} value
        match = re.match(r'^(\w+)(?:\{([^}]+)\})?\s+([\d.]+)', line)
        if not match:
            continue

        metric_name, labels_str, value_str = match.groups()
        value = float(value_str)

        # Extract labels
        labels = {}
        if labels_str:
            for label_pair in labels_str.split(','):
                if '=' in label_pair:
                    key, val = label_pair.split('=', 1)
                    labels[key.strip()] = val.strip('"')

        # Group metrics by name
        if metric_name not in metrics:
            metrics[metric_name] = []

        metrics[metric_name].append({
            'labels': labels,
            'value': value
        })

    return metrics


def get_metric_value(metrics: Dict, metric_name: str, default: float = 0.0) -> float:
    """
    Get the value of a metric (sum if multiple samples).

    Args:
        metrics: Parsed metrics dictionary.
        metric_name: Name of the metric.
        default: Default value if metric not found.

    Returns:
        Metric value.
    """
    if metric_name not in metrics:
        return default

    samples = metrics[metric_name]
    if not samples:
        return default

    # For counters and histograms, sum all samples
    return sum(s['value'] for s in samples)


def get_histogram_samples(metrics: Dict, metric_name: str, count: int = 10) -> List[float]:
    """
    Get recent samples from a histogram metric.

    Args:
        metrics: Parsed metrics dictionary.
        metric_name: Name of the histogram metric.
        count: Number of samples to return.

    Returns:
        List of sample values.
    """
    if metric_name not in metrics:
        return []

    samples = metrics[metric_name]
    # Extract bucket values (le label indicates bucket)
    values = [s['value'] for s in samples if 'le' in s.get('labels', {})]
    return values[-count:] if values else []


def get_metrics_summary() -> Dict[str, any]:
    """
    Get a summary of key metrics for the frontend.

    Returns:
        Dictionary with metrics summary.
    """
    metrics = parse_prometheus_metrics()

    return {
        'updates': {
            'total': get_metric_value(metrics, 'rag_updates_total'),
            'errors': get_metric_value(metrics, 'rag_update_errors_total'),
            'lag_samples': get_histogram_samples(metrics, 'rag_update_lag_seconds_bucket', 10),
        },
        'queries': {
            'total': get_metric_value(metrics, 'rag_queries_total'),
            'errors': get_metric_value(metrics, 'rag_query_errors_total'),
            'latency_samples': get_histogram_samples(metrics, 'rag_query_latency_seconds_bucket', 10),
        },
    }
