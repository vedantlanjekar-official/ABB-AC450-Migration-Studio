"""Dedicated thread pool for CPU-bound PDF conversion work.

FastAPI BackgroundTasks run on the asyncio event loop. Long-running PDF parsing
blocks the loop, which can cause Render health checks to fail and kill the worker
mid-conversion. A thread pool keeps the event loop responsive in production.
"""
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Set
import threading
from backend.core.logging import get_logger

logger = get_logger()

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ac450-convert")
_active_jobs: Set[str] = set()
_active_lock = threading.Lock()


def is_job_running(job_id: str) -> bool:
    """Return True if a conversion thread is actively running for this job."""
    with _active_lock:
        return job_id in _active_jobs


def submit_conversion_task(job_id: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Submit a conversion pipeline call to the shared worker thread pool."""
    with _active_lock:
        _active_jobs.add(job_id)

    def _wrapped() -> None:
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            logger.error(f"Unhandled conversion exception for job {job_id}: {exc}", exc_info=True)
            try:
                from backend.services.job_manager import job_store
                job_store.add_error(job_id, f"Unhandled conversion exception: {exc}")
                job_store.update_status(
                    job_id,
                    status="failed",
                    progress_percentage=100,
                    current_phase="Failed",
                    message=f"Conversion crashed: {exc}",
                )
            except Exception:
                logger.error(f"Failed to persist crash status for job {job_id}", exc_info=True)
            raise
        finally:
            with _active_lock:
                _active_jobs.discard(job_id)

    future: Future = _executor.submit(_wrapped)

    def _done(f: Future) -> None:
        with _active_lock:
            _active_jobs.discard(job_id)
        try:
            f.result()
        except Exception as exc:
            logger.error(f"Conversion future failed for job {job_id}: {exc}", exc_info=True)

    future.add_done_callback(_done)
