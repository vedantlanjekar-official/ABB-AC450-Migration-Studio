import shutil
from pathlib import Path
from backend.core.config import settings

def cleanup_job_files(job_id: str) -> None:
    """Cleans up temporary upload directory and files for a job."""
    upload_dir = settings.UPLOAD_DIR / job_id
    if upload_dir.exists():
        try:
            shutil.rmtree(upload_dir)
        except Exception:
            pass

def sanitize_filename(filename: str) -> str:
    """Sanitizes user uploaded filename."""
    return Path(filename).name.replace(" ", "_")
