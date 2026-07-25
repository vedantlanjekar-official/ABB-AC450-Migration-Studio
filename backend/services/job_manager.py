import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.schemas.api_schemas import ProcessStatusResponse, ElementTypeSummary

class JobManager:
    """In-memory thread-safe status & logs manager for processing jobs."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_id_or_files: Any, uploaded_files: Optional[List[str]] = None) -> str:
        """
        Creates a job entry. Accepts create_job(job_id, files) or create_job(files).
        """
        if isinstance(job_id_or_files, str) and uploaded_files is not None:
            job_id = job_id_or_files
            files = uploaded_files
        else:
            job_id = str(uuid.uuid4())
            files = job_id_or_files

        self._jobs[job_id] = {
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
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, **kwargs):
        if job_id in self._jobs:
            self._jobs[job_id].update(kwargs)
            self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

    def add_warning(self, job_id: str, warning: str):
        if job_id in self._jobs:
            if warning not in self._jobs[job_id]["warnings"]:
                self._jobs[job_id]["warnings"].append(warning)

    def add_error(self, job_id: str, error: str):
        if job_id in self._jobs:
            self._jobs[job_id]["errors"].append(error)

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
            processing_time_seconds=job.get("processing_time_seconds", 0.0),
            detected_element_types=element_summaries,
            generated_sheets=job.get("generated_sheets", []),
            preview_data=job.get("preview_data", {}),
            warnings=job.get("warnings", []),
            errors=job.get("errors", []),
            excel_file_path=job.get("excel_file_path")
        )

job_store = JobManager()
