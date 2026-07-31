import { useEffect, useRef } from 'react';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';
import { ProcessStatusResponse } from '../types/converter';

const POLL_INTERVAL_MS = 1000;
/** Large DB PDFs routinely take 4–10+ minutes (AST parse alone can exceed 4 min). */
const STUCK_JOB_TIMEOUT_MS = 20 * 60 * 1000;
/** Fail only when the backend stops sending any status/heartbeat signal. */
const NO_ACTIVITY_TIMEOUT_MS = 5 * 60 * 1000;

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

function activityKey(res: ProcessStatusResponse): string {
  // Prefer updated_at — heartbeats refresh it every ~15s without changing progress %.
  return [
    res.updated_at ?? '',
    res.progress_percentage ?? 0,
    res.current_phase ?? '',
    res.message ?? '',
    res.status ?? '',
  ].join('|');
}

export function useStatusPolling() {
  const { stage, jobId, setStatusResponse, setStage } = useConverterStore();
  const pollCountRef = useRef(0);
  const startedAtRef = useRef<number | null>(null);
  const lastActivityRef = useRef<{ key: string; at: number } | null>(null);

  useEffect(() => {
    if (stage !== 'processing' || !jobId) return;

    let isSubscribed = true;
    pollCountRef.current = 0;
    startedAtRef.current = Date.now();
    lastActivityRef.current = null;

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
          'Conversion timed out after 20 minutes. The backend may have restarted during processing. Please retry.',
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

        // Heartbeats update message without changing progress_percentage —
        // treat any status/message/phase change as proof the worker is alive.
        const key = activityKey(res);
        if (!lastActivityRef.current || lastActivityRef.current.key !== key) {
          lastActivityRef.current = { key, at: now };
        } else if (now - lastActivityRef.current.at > NO_ACTIVITY_TIMEOUT_MS) {
          failAndStop(
            'Conversion appears stuck with no backend activity. Please retry the upload.',
            `No status/heartbeat activity for 5 minutes (stuck at ${res.progress_percentage ?? 0}%).`
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
