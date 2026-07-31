import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.services.job_manager import job_store
from backend.schemas.api_schemas import FileUploadResponse
from backend.utils.file_utils import sanitize_filename

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = get_logger()

ALLOWED_SUFFIXES = (".pdf", ".xlsx", ".xlsm", ".xls")


@router.post("", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Receives PDF conversion or standalone Excel workflow uploads.
    Saves files to job directory and returns job_id.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    job_id = str(uuid.uuid4())
    job_upload_dir = settings.UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload started for job {job_id} — target dir {job_upload_dir}")

    saved_filenames = []

    for file in files:
        name_lower = (file.filename or "").lower()
        if not name_lower.endswith(ALLOWED_SUFFIXES):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid file extension for {file.filename}. "
                    "Supported: PDF, XLSX, XLSM, XLS."
                ),
            )

        safe_name = sanitize_filename(file.filename)
        dest_path = job_upload_dir / safe_name

        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds max allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        with open(dest_path, "wb") as f:
            f.write(content)
        logger.info(f"Saved upload {safe_name} ({len(content)} bytes) for job {job_id}")

        saved_filenames.append(safe_name)

    job_store.create_job(job_id, saved_filenames)
    logger.info(f"Upload complete for job {job_id}: {saved_filenames}")

    return FileUploadResponse(
        job_id=job_id,
        uploaded_files=saved_filenames,
        total_files=len(saved_filenames),
        message=f"Uploaded {len(saved_filenames)} file(s) successfully. Job ID: {job_id}",
    )
