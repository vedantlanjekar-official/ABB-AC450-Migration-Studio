import { useEffect } from 'react';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';

export function useStatusPolling() {
  const { stage, jobId, setStatusResponse, setStage } = useConverterStore();

  useEffect(() => {
    if (stage !== 'processing' || !jobId) return;

    let isSubscribed = true;

    const pollStatus = async () => {
      try {
        const res = await apiClient.getJobStatus(jobId);
        if (!isSubscribed) return;

        setStatusResponse(res);

        if (res.status === 'completed') {
          setStage('results');
        } else if (res.status === 'failed') {
          setStage('results');
        }
      } catch (err) {
        console.error('Error polling status:', err);
      }
    };

    // Initial fetch
    pollStatus();

    // Poll every 500ms
    const intervalId = setInterval(pollStatus, 500);

    return () => {
      isSubscribed = false;
      clearInterval(intervalId);
    };
  }, [stage, jobId, setStatusResponse, setStage]);
}
