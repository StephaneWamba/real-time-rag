"""Retry logic for failed operations."""

import asyncio
import logging
from typing import Callable, TypeVar, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: Optional[int] = None,
    delay: Optional[float] = None,
    backoff_multiplier: Optional[float] = None,
    exceptions: tuple = (Exception,),
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry.
        max_retries: Maximum number of retry attempts.
        delay: Initial delay in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        exceptions: Tuple of exceptions to catch and retry.

    Returns:
        Result of the function call.

    Raises:
        Last exception if all retries fail.
    """
    max_retries = max_retries or settings.max_retries
    delay = delay or settings.retry_delay_seconds
    backoff_multiplier = backoff_multiplier or settings.retry_backoff_multiplier

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = delay * (backoff_multiplier ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                    f"Retrying in {wait_time:.2f}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"All {max_retries + 1} attempts failed. Last error: {str(e)}")

    raise last_exception
