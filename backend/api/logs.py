from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from backend.core.config import settings

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("/{job_id}", response_class=PlainTextResponse)
async def get_job_log(job_id: str):
    """
    Returns text log content generated during job processing.
    """
    log_file = settings.LOG_DIR / f"{job_id}.log"
    if not log_file.exists():
        return f"Log file for job {job_id} does not exist yet."

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")
