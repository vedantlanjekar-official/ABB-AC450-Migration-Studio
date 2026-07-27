from fastapi import APIRouter, HTTPException
from backend.schemas.api_schemas import ProcessRequest
from backend.services.job_manager import job_store, PROCESSING_STATUSES
from backend.services.conversion_service import ConversionService
from backend.services.pipeline_executor import submit_conversion_task, is_job_running
from backend.core.logging import get_logger

router = APIRouter(prefix="/process", tags=["Process"])
logger = get_logger()


@router.post("")
async def start_conversion_process(request: ProcessRequest):
    """Triggers DB or PC conversion in a background worker thread for the given job_id."""
    job = job_store.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {request.job_id} not found.")

    status = job.get("status")
    actively_running = is_job_running(request.job_id)
    stale = job_store.is_stale(request.job_id)

    # Allow retry when a previous worker died mid-conversion (common on Render free tier).
    if status in PROCESSING_STATUSES and actively_running and not stale:
        return {
            "job_id": request.job_id,
            "status": status,
            "message": "Job is already processing.",
        }

    if status in PROCESSING_STATUSES and (stale or not actively_running):
        logger.warning(
            f"Re-queueing stuck job {request.job_id} "
            f"(status={status}, stale={stale}, running={actively_running})"
        )

    conversion_type = (request.conversion_type or "DB").upper()

    job_store.update_status(
        request.job_id,
        status="queued",
        progress_percentage=5,
        current_phase="Queued",
        conversion_type=conversion_type,
        errors=[],
        message=f"Conversion pipeline ({conversion_type}) queued for background execution.",
    )

    service = ConversionService(request.job_id)
    submit_conversion_task(request.job_id, service.run_conversion_pipeline, conversion_type)

    return {
        "job_id": request.job_id,
        "conversion_type": conversion_type,
        "status": "queued",
        "message": f"Conversion pipeline ({conversion_type}) started in background.",
    }
