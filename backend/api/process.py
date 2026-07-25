from fastapi import APIRouter, BackgroundTasks, HTTPException
from backend.schemas.api_schemas import ProcessRequest
from backend.services.job_manager import job_store
from backend.services.conversion_service import ConversionService

router = APIRouter(prefix="/process", tags=["Process"])

@router.post("")
async def start_conversion_process(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Triggers asynchronous DB or PC conversion processing pipeline for a given job_id.
    """
    job = job_store.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {request.job_id} not found.")

    if job["status"] in ("reading_pdf", "extracting_text", "detecting_elements", "parsing_parameters", "grouping_elements", "generating_excel"):
        return {"job_id": request.job_id, "message": "Job is already processing."}

    conversion_type = (request.conversion_type or "DB").upper()
    service = ConversionService(request.job_id)
    background_tasks.add_task(service.run_conversion_pipeline, conversion_type)

    return {
        "job_id": request.job_id,
        "conversion_type": conversion_type,
        "status": "queued",
        "message": f"Conversion pipeline ({conversion_type}) started in background."
    }
