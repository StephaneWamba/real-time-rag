"""Dead Letter Queue service for failed events."""

import json
import logging
import time
from typing import Optional

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.exceptions import DLQError

logger = logging.getLogger(__name__)


class DLQService:
    """Service for sending failed events to Dead Letter Queue."""

    def __init__(self) -> None:
        """Initialize the DLQ service."""
        self.producer: Optional[AIOKafkaProducer] = None
        self.enabled = settings.dlq_enabled

    async def connect(self) -> None:
        """Connect to Kafka for DLQ."""
        if not self.enabled:
            return

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self.producer.start()
            logger.info("DLQ service connected")
        except Exception as e:
            logger.error(f"Failed to connect DLQ service: {str(e)}")
            raise DLQError(f"Failed to connect DLQ service: {str(e)}") from e

    async def disconnect(self) -> None:
        """Disconnect from Kafka."""
        if self.producer:
            await self.producer.stop()

    async def send_failed_event(
        self,
        event_data: dict,
        error: str,
        original_topic: str,
        offset: Optional[int] = None,
        partition: Optional[int] = None,
    ) -> None:
        """
        Send a failed event to the Dead Letter Queue.

        Args:
            event_data: Original event data that failed.
            error: Error message describing the failure.
            original_topic: Original Kafka topic.
            offset: Original message offset.
            partition: Original message partition.
        """
        if not self.enabled or not self.producer:
            logger.warning("DLQ is disabled, not sending failed event")
            return

        try:
            dlq_message = {
                "original_event": event_data,
                "error": error,
                "original_topic": original_topic,
                "offset": offset,
                "partition": partition,
                "timestamp": time.time(),
            }

            await self.producer.send_and_wait(
                settings.dlq_topic,
                value=dlq_message,
            )
            logger.info(
                f"Sent failed event to DLQ: topic={original_topic}, "
                f"offset={offset}, error={error[:100]}"
            )
        except Exception as e:
            logger.error(f"Failed to send event to DLQ: {str(e)}")
            raise DLQError(f"Failed to send event to DLQ: {str(e)}") from e
