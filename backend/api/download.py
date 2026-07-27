from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.services.job_manager import job_store
from backend.core.config import settings

router = APIRouter(prefix="/download", tags=["Download"])

@router.get("/{job_id}")
async def download_excel_export(job_id: str):
    """
    Downloads generated Valmet-compatible Excel workbook for a completed job.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed yet. Current status: {job['status']}")

    excel_path_str = job.get("excel_file_path")
    if not excel_path_str or not Path(excel_path_str).exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Generated Excel export file not found. "
                "The server may have restarted after conversion — please run the conversion again."
            ),
        )

    export_filename = f"ABB_AC450_Valmet_Export_{job_id[:8]}.xlsx"

    return FileResponse(
        path=excel_path_str,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=export_filename
    )
