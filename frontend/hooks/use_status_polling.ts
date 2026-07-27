import { useEffect, useRef } from 'react';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';

const POLL_INTERVAL_MS = 1000;
const STUCK_JOB_TIMEOUT_MS = 10 * 60 * 1000;

export function useStatusPolling() {
  const { stage, jobId, setStatusResponse, setStage } = useConverterStore();
  const pollCountRef = useRef(0);
  const startedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (stage !== 'processing' || !jobId) return;

    let isSubscribed = true;
    pollCountRef.current = 0;
    startedAtRef.current = Date.now();

    const pollStatus = async () => {
      if (!isSubscribed) return;

      pollCountRef.current += 1;

      if (startedAtRef.current && Date.now() - startedAtRef.current > STUCK_JOB_TIMEOUT_MS) {
        setStatusResponse({
          job_id: jobId,
          status: 'failed',
          progress_percentage: 100,
          current_phase: 'Timed Out',
          message:
            'Conversion timed out after 10 minutes. The backend may have restarted during processing. Please retry.',
          total_objects: 0,
          default_sections_found: 0,
          hardware_default_blocks: 0,
          software_default_blocks: 0,
          standalone_default_blocks: 0,
          merged_profiles_created: 0,
          objects_inherited_defaults: 0,
          parameters_filled_from_defaults: 0,
          object_overrides: 0,
          missing_parameters_after_merge: 0,
          ignored_header_footer_lines: 0,
          processing_time_seconds: 0,
          detected_element_types: [],
          generated_sheets: [],
          preview_data: {},
          warnings: [],
          errors: ['Conversion timed out waiting for backend completion.'],
          excel_file_path: null,
        });
        setStage('results');
        return;
      }

      try {
        const res = await apiClient.getJobStatus(jobId);
        if (!isSubscribed) return;

        setStatusResponse(res);

        if (res.status === 'completed' || res.status === 'failed') {
          setStage('results');
        }
      } catch (err: unknown) {
        console.error('Error polling status:', err);
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosErr.response?.status === 404 && pollCountRef.current > 5) {
          setStatusResponse({
            job_id: jobId,
            status: 'failed',
            progress_percentage: 100,
            current_phase: 'Job Not Found',
            message:
              'The conversion job was lost on the server. This can happen when the backend restarts. Please upload again.',
            total_objects: 0,
            default_sections_found: 0,
            hardware_default_blocks: 0,
            software_default_blocks: 0,
            standalone_default_blocks: 0,
            merged_profiles_created: 0,
            objects_inherited_defaults: 0,
            parameters_filled_from_defaults: 0,
            object_overrides: 0,
            missing_parameters_after_merge: 0,
            ignored_header_footer_lines: 0,
            processing_time_seconds: 0,
            detected_element_types: [],
            generated_sheets: [],
            preview_data: {},
            warnings: [],
            errors: [axiosErr.response?.data?.detail || 'Job ID not found on backend.'],
            excel_file_path: null,
          });
          setStage('results');
        }
      }
    };

    pollStatus();
    const intervalId = setInterval(pollStatus, POLL_INTERVAL_MS);

    return () => {
      isSubscribed = false;
      clearInterval(intervalId);
    };
  }, [stage, jobId, setStatusResponse, setStage]);
}
