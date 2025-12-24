"""Batch processing service for high-volume updates."""

import asyncio
import logging
from collections import deque
from typing import Callable, List, Optional, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BatchProcessor:
    """Process items in batches for improved throughput."""

    def __init__(
        self,
        batch_size: int = None,
        batch_timeout: float = None,
        process_batch: Callable[[List[T]], None] = None,
    ) -> None:
        """
        Initialize batch processor.

        Args:
            batch_size: Maximum items per batch.
            batch_timeout: Maximum time to wait before processing batch.
            process_batch: Async function to process a batch of items.
        """
        self.batch_size = batch_size or settings.batch_size
        self.batch_timeout = batch_timeout or settings.batch_timeout_seconds
        self.process_batch = process_batch
        self.buffer: deque = deque()
        self.last_batch_time = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def add(self, item: T) -> None:
        """
        Add an item to the batch buffer.

        Args:
            item: Item to add to batch.
        """
        async with self._lock:
            self.buffer.append(item)
            
            if len(self.buffer) >= self.batch_size:
                await self._process_batch()
            else:
                if self._task is None or self._task.done():
                    self._task = asyncio.create_task(self._timeout_processor())

    async def _timeout_processor(self) -> None:
        """Process batch after timeout if buffer has items."""
        await asyncio.sleep(self.batch_timeout)
        async with self._lock:
            if self.buffer and (asyncio.get_event_loop().time() - self.last_batch_time) >= self.batch_timeout:
                await self._process_batch()

    async def _process_batch(self) -> None:
        """Process the current batch."""
        if not self.buffer or not self.process_batch:
            return
        
        batch = [self.buffer.popleft() for _ in range(min(self.batch_size, len(self.buffer)))]
        self.last_batch_time = asyncio.get_event_loop().time()
        
        try:
            if asyncio.iscoroutinefunction(self.process_batch):
                await self.process_batch(batch)
            else:
                self.process_batch(batch)
            logger.info(f"Processed batch of {len(batch)} items")
        except Exception as e:
            logger.error(f"Failed to process batch: {str(e)}")
            raise

    async def flush(self) -> None:
        """Flush remaining items in buffer."""
        async with self._lock:
            while self.buffer:
                await self._process_batch()

