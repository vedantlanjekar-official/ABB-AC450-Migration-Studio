from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class FileUploadResponse(BaseModel):
    job_id: str
    uploaded_files: List[str]
    total_files: int
    message: str

class ProcessRequest(BaseModel):
    job_id: str
    conversion_type: Optional[str] = "DB"  # "DB" or "PC"

class ElementTypeSummary(BaseModel):
    element_type: str
    count: int
    sample_tags: List[str]

class ProcessStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percentage: int
    current_phase: str
    message: str
    conversion_type: Optional[str] = "DB"
    total_objects: int = 0
    default_sections_found: int = 0
    hardware_default_blocks: int = 0
    software_default_blocks: int = 0
    standalone_default_blocks: int = 0
    merged_profiles_created: int = 0
    objects_inherited_defaults: int = 0
    parameters_filled_from_defaults: int = 0
    object_overrides: int = 0
    missing_parameters_after_merge: int = 0
    ignored_header_footer_lines: int = 0
    ai_count: int = 0
    ao_count: int = 0
    di_count: int = 0
    do_count: int = 0
    duplicate_records: int = 0
    missing_descriptions: int = 0
    processing_time_seconds: float = 0.0
    detected_element_types: List[ElementTypeSummary] = []
    generated_sheets: List[str] = []
    preview_data: Dict[str, List[Dict[str, Any]]] = {}
    warnings: List[str] = []
    errors: List[str] = []
    excel_file_path: Optional[str] = None
