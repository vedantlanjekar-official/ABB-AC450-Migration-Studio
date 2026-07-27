import { useEffect, useRef } from 'react';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';
import { ProcessStatusResponse } from '../types/converter';

const POLL_INTERVAL_MS = 1000;
const STUCK_JOB_TIMEOUT_MS = 3 * 60 * 1000;

function buildFailedStatus(jobId: string, message: string, detail: string): ProcessStatusResponse {
  return {
    job_id: jobId,
    status: 'failed',
    progress_percentage: 100,
    current_phase: 'Failed',
    message,
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
    errors: [detail],
    excel_file_path: null,
  };
}

export function useStatusPolling() {
  const { stage, jobId, setStatusResponse, setStage } = useConverterStore();
  const pollCountRef = useRef(0);
  const startedAtRef = useRef<number | null>(null);
  const lastProgressRef = useRef<{ progress: number; at: number } | null>(null);

  useEffect(() => {
    if (stage !== 'processing' || !jobId) return;

    let isSubscribed = true;
    pollCountRef.current = 0;
    startedAtRef.current = Date.now();
    lastProgressRef.current = null;

    const failAndStop = (message: string, detail: string) => {
      if (!isSubscribed) return;
      setStatusResponse(buildFailedStatus(jobId, message, detail));
      setStage('results');
    };

    const pollStatus = async () => {
      if (!isSubscribed) return;

      pollCountRef.current += 1;
      const now = Date.now();

      if (startedAtRef.current && now - startedAtRef.current > STUCK_JOB_TIMEOUT_MS) {
        failAndStop(
          'Conversion timed out after 3 minutes. The backend may have restarted during processing. Please retry.',
          'Conversion timed out waiting for backend completion.'
        );
        return;
      }

      try {
        const res = await apiClient.getJobStatus(jobId);
        if (!isSubscribed) return;

        setStatusResponse(res);

        if (res.status === 'completed' || res.status === 'failed') {
          setStage('results');
          return;
        }

        const progress = res.progress_percentage ?? 0;
        if (
          !lastProgressRef.current ||
          lastProgressRef.current.progress !== progress
        ) {
          lastProgressRef.current = { progress, at: now };
        } else if (now - lastProgressRef.current.at > 120000) {
          failAndStop(
            'Conversion appears stuck with no progress. Please retry the upload.',
            `No progress for 2 minutes (stuck at ${progress}%).`
          );
        }
      } catch (err: unknown) {
        console.error('Error polling status:', err);
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosErr.response?.status === 404 && pollCountRef.current > 5) {
          failAndStop(
            'The conversion job was lost on the server. This can happen when the backend restarts. Please upload again.',
            axiosErr.response?.data?.detail || 'Job ID not found on backend.'
          );
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
