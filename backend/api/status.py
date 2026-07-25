from fastapi import APIRouter, HTTPException
from backend.schemas.api_schemas import ProcessStatusResponse
from backend.services.job_manager import job_store

router = APIRouter(prefix="/status", tags=["Status"])

@router.get("/{job_id}", response_model=ProcessStatusResponse)
async def get_job_status(job_id: str):
    """
    Returns real-time processing status, progress percentage, metrics, and warnings for a job.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")

    # Filter dictionary keys matching ProcessStatusResponse schema fields
    valid_keys = ProcessStatusResponse.model_fields.keys()
    filtered_job = {k: v for k, v in job.items() if k in valid_keys}

    return ProcessStatusResponse(**filtered_job)
