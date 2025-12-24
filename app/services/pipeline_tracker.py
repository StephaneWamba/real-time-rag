"""Pipeline activity tracker for frontend visualization."""

import datetime
from typing import Dict, Optional

# In-memory tracker for recent pipeline activity
pipeline_activity: Dict = {
    'last_update_time': None,
    'recent_updates': [],
    'stage_latencies': {
        'postgresql': 0.0,
        'debezium': 0.0,
        'kafka': 0.0,
        'update_service': 0.0,
        'embedding': 0.0,
        'qdrant': 0.0,
    },
}


def update_pipeline_activity(
    stage_latencies: Dict[str, float],
    document_id: Optional[str] = None,
) -> None:
    """
    Update pipeline activity tracker.

    Args:
        stage_latencies: Dictionary of stage names to latencies.
        document_id: Optional document ID for tracking.
    """
    pipeline_activity['stage_latencies'] = stage_latencies
    pipeline_activity['last_update_time'] = datetime.datetime.now().isoformat()
    
    if document_id:
        pipeline_activity['recent_updates'].append({
            'document_id': str(document_id),
            'timestamp': pipeline_activity['last_update_time'],
            'total_latency': sum(stage_latencies.values()),
        })
        # Keep only last 10 updates
        pipeline_activity['recent_updates'] = pipeline_activity['recent_updates'][-10:]


def get_pipeline_status() -> Dict:
    """
    Get current pipeline status.

    Returns:
        Pipeline status dictionary.
    """
    return {
        'stages': pipeline_activity['stage_latencies'],
        'total_latency': sum(pipeline_activity['stage_latencies'].values()),
        'last_update': pipeline_activity.get('last_update_time'),
        'recent_updates_count': len(pipeline_activity['recent_updates']),
    }

