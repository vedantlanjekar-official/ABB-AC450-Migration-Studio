import uuid
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.schemas.api_schemas import ProcessStatusResponse, ElementTypeSummary

_logger = get_logger()

PROCESSING_STATUSES = {
    "queued",
    "reading_pdf",
    "extracting_text",
    "detecting_elements",
    "parsing_parameters",
    "grouping_elements",
    "generating_excel",
}

# Jobs with no heartbeat for this long are considered dead (worker crash / OOM).
STALE_JOB_SECONDS = 120


class JobManager:
    """Job status manager with in-memory cache and file-backed JSON persistence.

    Render and other PaaS hosts may restart workers or route requests across
    processes. Persisting job state to the temp directory keeps upload/process/status
    consistent across the conversion lifecycle.
    """

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def _get_job_file(self, job_id: str) -> Path:
        return settings.LOG_DIR / f"{job_id}_job.json"

    def _save_job_to_disk(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        try:
            settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
            job_file = self._get_job_file(job_id)
            with open(job_file, "w", encoding="utf-8") as f:
                json.dump(job, f, indent=2, default=str)
        except Exception as exc:
            _logger.error(f"Failed to persist job {job_id} to disk: {exc}", exc_info=True)

    def _load_job_from_disk(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_file = self._get_job_file(job_id)
        if not job_file.exists():
            return None
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                job_data = json.load(f)
                self._jobs[job_id] = job_data
                return job_data
        except Exception as exc:
            _logger.error(f"Failed to load job {job_id} from disk: {exc}", exc_info=True)
            return None

    def create_job(self, job_id_or_files: Any, uploaded_files: Optional[List[str]] = None) -> str:
        """Creates a job entry. Accepts create_job(job_id, files) or create_job(files)."""
        if isinstance(job_id_or_files, str) and uploaded_files is not None:
            job_id = job_id_or_files
            files = uploaded_files
        else:
            job_id = str(uuid.uuid4())
            files = job_id_or_files

        job_data = {
            "job_id": job_id,
            "status": "idle",
            "progress_percentage": 0,
            "current_phase": "Uploaded",
            "message": "Files uploaded successfully.",
            "uploaded_files": files,
            "total_objects": 0,
            "default_sections_found": 0,
            "hardware_default_blocks": 0,
            "software_default_blocks": 0,
            "standalone_default_blocks": 0,
            "merged_profiles_created": 0,
            "objects_inherited_defaults": 0,
            "parameters_filled_from_defaults": 0,
            "object_overrides": 0,
            "missing_parameters_after_merge": 0,
            "ignored_header_footer_lines": 0,
            "processing_time_seconds": 0.0,
            "detected_element_types": [],
            "generated_sheets": [],
            "preview_data": {},
            "warnings": [],
            "errors": [],
            "excel_file_path": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        self._jobs[job_id] = job_data
        self._save_job_to_disk(job_id)
        _logger.info(f"Created job {job_id} with {len(files)} uploaded file(s): {files}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id not in self._jobs:
            self._load_job_from_disk(job_id)
        return self._jobs.get(job_id)

    def _parse_updated_at(self, job: Dict[str, Any]) -> Optional[datetime]:
        raw = job.get("updated_at")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", ""))
        except Exception:
            return None

    def is_processing(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        return bool(job and job.get("status") in PROCESSING_STATUSES)

    def is_stale(self, job_id: str, max_age_seconds: int = STALE_JOB_SECONDS) -> bool:
        """True when a job is marked processing but has not heartbeated recently."""
        job = self.get_job(job_id)
        if not job or job.get("status") not in PROCESSING_STATUSES:
            return False
        updated = self._parse_updated_at(job)
        if not updated:
            return True
        return datetime.utcnow() - updated > timedelta(seconds=max_age_seconds)

    def heartbeat(self, job_id: str, message: Optional[str] = None) -> None:
        """Touch updated_at so status polling knows the worker is still alive."""
        job = self.get_job(job_id)
        if not job:
            return
        if message:
            job["message"] = message
        job["updated_at"] = datetime.utcnow().isoformat()
        self._jobs[job_id] = job
        self._save_job_to_disk(job_id)

    def mark_stale_failed(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Mark a stuck processing job as failed so the UI can recover."""
        job = self.get_job(job_id)
        if not job or not self.is_stale(job_id):
            return job
        error = (
            "Conversion worker stopped unexpectedly (timeout or server restart). "
            "Please upload again and retry."
        )
        if error not in job.get("errors", []):
            job.setdefault("errors", []).append(error)
        job.update({
            "status": "failed",
            "progress_percentage": 100,
            "current_phase": "Failed",
            "message": error,
            "updated_at": datetime.utcnow().isoformat(),
        })
        self._jobs[job_id] = job
        self._save_job_to_disk(job_id)
        _logger.error(f"Marked stale job {job_id} as failed")
        return job

    def update_status(self, job_id: str, **kwargs):
        job = self.get_job(job_id)
        if job:
            job.update(kwargs)
            job["updated_at"] = datetime.utcnow().isoformat()
            self._jobs[job_id] = job
            self._save_job_to_disk(job_id)
            _logger.info(
                f"Job {job_id} status={job.get('status')} "
                f"progress={job.get('progress_percentage')}% "
                f"phase={job.get('current_phase')}"
            )

    def add_warning(self, job_id: str, warning: str):
        job = self.get_job(job_id)
        if job:
            if warning not in job["warnings"]:
                job["warnings"].append(warning)
                job["updated_at"] = datetime.utcnow().isoformat()
                self._save_job_to_disk(job_id)
                _logger.warning(f"Job {job_id} warning: {warning}")

    def add_error(self, job_id: str, error: str):
        job = self.get_job(job_id)
        if job:
            job["errors"].append(error)
            job["updated_at"] = datetime.utcnow().isoformat()
            self._save_job_to_disk(job_id)
            _logger.error(f"Job {job_id} error: {error}")

    def get_status_response(self, job_id: str) -> Optional[ProcessStatusResponse]:
        job = self.get_job(job_id)
        if not job:
            return None

        element_summaries = []
        for raw in job.get("detected_element_types", []):
            if isinstance(raw, dict):
                element_summaries.append(ElementTypeSummary(**raw))
            elif isinstance(raw, ElementTypeSummary):
                element_summaries.append(raw)

        return ProcessStatusResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress_percentage=job["progress_percentage"],
            current_phase=job["current_phase"],
            message=job["message"],
            conversion_type=job.get("conversion_type", "DB"),
            total_objects=job.get("total_objects", 0),
            default_sections_found=job.get("default_sections_found", 0),
            hardware_default_blocks=job.get("hardware_default_blocks", 0),
            software_default_blocks=job.get("software_default_blocks", 0),
            standalone_default_blocks=job.get("standalone_default_blocks", 0),
            merged_profiles_created=job.get("merged_profiles_created", 0),
            objects_inherited_defaults=job.get("objects_inherited_defaults", 0),
            parameters_filled_from_defaults=job.get("parameters_filled_from_defaults", 0),
            object_overrides=job.get("object_overrides", 0),
            missing_parameters_after_merge=job.get("missing_parameters_after_merge", 0),
            ignored_header_footer_lines=job.get("ignored_header_footer_lines", 0),
            ai_count=job.get("ai_count", 0),
            ao_count=job.get("ao_count", 0),
            di_count=job.get("di_count", 0),
            do_count=job.get("do_count", 0),
            duplicate_records=job.get("duplicate_records", 0),
            missing_descriptions=job.get("missing_descriptions", 0),
            processing_time_seconds=job.get("processing_time_seconds", 0.0),
            detected_element_types=element_summaries,
            generated_sheets=job.get("generated_sheets", []),
            preview_data=job.get("preview_data", {}),
            warnings=job.get("warnings", []),
            errors=job.get("errors", []),
            excel_file_path=job.get("excel_file_path")
        )


job_store = JobManager()
