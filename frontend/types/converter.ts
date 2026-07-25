export type ConversionStatus =
  | 'idle'
  | 'reading_pdf'
  | 'extracting_text'
  | 'detecting_elements'
  | 'grouping_elements'
  | 'generating_excel'
  | 'completed'
  | 'failed';

export type PipelineStage = 'upload' | 'processing' | 'results';

export interface FileUploadResponse {
  job_id: string;
  uploaded_files: string[];
  total_files: number;
  message: string;
}

export interface ElementTypeSummary {
  element_type: string;
  count: number;
  sample_tags: string[];
}

export interface ProcessStatusResponse {
  job_id: string;
  status: ConversionStatus;
  progress_percentage: number;
  current_phase: string;
  message: string;
  conversion_type?: 'DB' | 'PC';
  total_objects: number;
  default_sections_found: number;
  hardware_default_blocks: number;
  software_default_blocks: number;
  standalone_default_blocks: number;
  merged_profiles_created: number;
  objects_inherited_defaults: number;
  parameters_filled_from_defaults: number;
  object_overrides: number;
  missing_parameters_after_merge: number;
  ignored_header_footer_lines: number;
  ai_count?: number;
  ao_count?: number;
  di_count?: number;
  do_count?: number;
  duplicate_records?: number;
  missing_descriptions?: number;
  processing_time_seconds: number;
  detected_element_types: ElementTypeSummary[];
  generated_sheets: string[];
  preview_data: Record<string, Record<string, unknown>[]>;
  warnings: string[];
  errors: string[];
  excel_file_path: string | null;
}
