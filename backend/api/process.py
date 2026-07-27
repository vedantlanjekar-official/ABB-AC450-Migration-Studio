from fastapi import APIRouter, HTTPException
from backend.schemas.api_schemas import ProcessRequest
from backend.services.job_manager import job_store
from backend.services.conversion_service import ConversionService
from backend.services.pipeline_executor import submit_conversion_task

router = APIRouter(prefix="/process", tags=["Process"])

PROCESSING_STATUSES = (
    "queued",
    "reading_pdf",
    "extracting_text",
    "detecting_elements",
    "parsing_parameters",
    "grouping_elements",
    "generating_excel",
)


@router.post("")
async def start_conversion_process(request: ProcessRequest):
    """Triggers DB or PC conversion in a background worker thread for the given job_id."""
    job = job_store.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {request.job_id} not found.")

    if job["status"] in PROCESSING_STATUSES:
        return {"job_id": request.job_id, "message": "Job is already processing."}

    conversion_type = (request.conversion_type or "DB").upper()

    job_store.update_status(
        request.job_id,
        status="queued",
        progress_percentage=5,
        current_phase="Queued",
        conversion_type=conversion_type,
        message=f"Conversion pipeline ({conversion_type}) queued for background execution.",
    )

    service = ConversionService(request.job_id)
    submit_conversion_task(service.run_conversion_pipeline, conversion_type)

    return {
        "job_id": request.job_id,
        "conversion_type": conversion_type,
        "status": "queued",
        "message": f"Conversion pipeline ({conversion_type}) started in background.",
    }
