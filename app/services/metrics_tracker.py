"""Track recent metric samples for real-time visualization."""

from collections import deque
from typing import Deque
import threading

# Thread-safe storage for recent samples
_update_lag_samples: Deque[float] = deque(maxlen=100)
_query_latency_samples: Deque[float] = deque(maxlen=100)
_lock = threading.Lock()


def add_update_lag_sample(lag: float) -> None:
    """
    Add an update lag sample.
    
    Args:
        lag: Lag time in seconds.
    """
    with _lock:
        _update_lag_samples.append(lag)


def add_query_latency_sample(latency: float) -> None:
    """
    Add a query latency sample.
    
    Args:
        latency: Latency time in seconds.
    """
    with _lock:
        _query_latency_samples.append(latency)


def get_update_lag_samples(count: int = 10) -> list[float]:
    """
    Get recent update lag samples.
    
    Args:
        count: Number of samples to return.
        
    Returns:
        List of lag values in seconds.
    """
    with _lock:
        return list(_update_lag_samples)[-count:]


def get_query_latency_samples(count: int = 10) -> list[float]:
    """
    Get recent query latency samples.
    
    Args:
        count: Number of samples to return.
        
    Returns:
        List of latency values in seconds.
    """
    with _lock:
        return list(_query_latency_samples)[-count:]

