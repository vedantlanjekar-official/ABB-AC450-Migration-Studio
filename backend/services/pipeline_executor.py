"""Dedicated thread pool for CPU-bound PDF conversion work.

FastAPI BackgroundTasks run on the asyncio event loop. Long-running PDF parsing
blocks the loop, which can cause Render health checks to fail and kill the worker
mid-conversion. A thread pool keeps the event loop responsive in production.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ac450-convert")


def submit_conversion_task(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Submit a conversion pipeline call to the shared worker thread pool."""
    _executor.submit(fn, *args, **kwargs)
