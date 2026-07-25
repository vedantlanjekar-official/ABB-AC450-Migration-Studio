import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';

export function useConverterJob() {
  const { jobId, stage, setStatusResponse, setStage } = useConverterStore();

  const query = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => apiClient.getJobStatus(jobId!),
    enabled: !!jobId && stage === 'processing',
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 800;
      if (data.status === 'completed' || data.status === 'failed') {
        return false;
      }
      return 800;
    },
  });

  useEffect(() => {
    if (query.data) {
      setStatusResponse(query.data);
      if (query.data.status === 'completed') {
        setStage('results');
      }
    }
  }, [query.data, setStatusResponse, setStage]);

  return query;
}
