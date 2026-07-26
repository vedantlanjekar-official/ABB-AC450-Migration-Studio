import { useState } from 'react';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';

export function useFileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { selectedFiles, conversionType, setJobId, setStage } = useConverterStore();

  const startConversion = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setError('Please select at least one PDF file.');
      return;
    }

    try {
      setIsUploading(true);
      setError(null);

      // 1. Upload files
      const uploadRes = await apiClient.uploadFiles(selectedFiles);
      const newJobId = uploadRes.job_id;
      setJobId(newJobId);

      // 2. Trigger background process with conversionType
      await apiClient.triggerProcess(newJobId, conversionType);

      // 3. Move to processing stage
      setStage('processing');
    } catch (err: any) {
      console.error('Upload / process trigger error:', err);
      let msg = 'Failed to upload and start conversion process.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          msg = detail;
        } else if (Array.isArray(detail)) {
          msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        } else {
          msg = JSON.stringify(detail);
        }
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return {
    startConversion,
    isUploading,
    error,
  };
}
