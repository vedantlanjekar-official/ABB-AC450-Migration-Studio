import { useState } from 'react';
import { useConverterStore } from '../store/converter_store';
import { apiClient } from '../services/api_client';
import { ConversionType } from '../types/converter';

const COLD_START_RETRIES = 3;
const COLD_START_DELAY_MS = 8000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientNetworkError(err: unknown): boolean {
  const e = err as { code?: string; message?: string; response?: { status?: number } };
  if (!e.response) return true;
  const status = e.response.status;
  return status === 502 || status === 503 || status === 504;
}

async function withColdStartRetry<T>(fn: () => Promise<T>): Promise<T> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= COLD_START_RETRIES; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      if (attempt < COLD_START_RETRIES && isTransientNetworkError(err)) {
        await sleep(COLD_START_DELAY_MS * attempt);
        continue;
      }
      throw err;
    }
  }
  throw lastError;
}

export function useFileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    selectedFiles,
    conversionType,
    compareFile1,
    compareFile2,
    arrangementFile,
    templateFile,
    setJobId,
    setStage,
  } = useConverterStore();

  const startConversion = async (conversionTypeOverride?: ConversionType) => {
    const requestedType = conversionTypeOverride || conversionType;
    const isCompare = requestedType === 'COMPARE';
    const isArrangement = requestedType === 'IO_ARRANGE';
    const isTemplate = requestedType === 'ENG_TEMPLATE';

    if (isCompare) {
      if (!compareFile1 || !compareFile2) {
        setError('Please upload both Excel files (Worksheet 1 and Worksheet 2).');
        return;
      }
    } else if (isArrangement) {
      if (!arrangementFile) {
        setError('Please upload one generated DB or PB/PC Excel file.');
        return;
      }
    } else if (isTemplate) {
      if (!templateFile) {
        setError('Please upload one generated DB or PB/PC Excel file.');
        return;
      }
    } else if (!selectedFiles || selectedFiles.length === 0) {
      setError('Please select at least one PDF, AAX, or BAX file.');
      return;
    }

    try {
      setIsUploading(true);
      setError(null);

      const filesToUpload = isCompare
        ? [compareFile1 as File, compareFile2 as File]
        : isArrangement
        ? [arrangementFile as File]
        : isTemplate
        ? [templateFile as File]
        : selectedFiles;

      // Retry on Render free-tier cold starts (30–60s wake).
      const uploadRes = await withColdStartRetry(() => apiClient.uploadFiles(filesToUpload));
      const newJobId = uploadRes.job_id;
      setJobId(newJobId);

      await withColdStartRetry(() => apiClient.triggerProcess(newJobId, requestedType));

      setStage('processing');
    } catch (err: any) {
      console.error('Upload / process trigger error:', err);
      let msg = isCompare
        ? 'Failed to upload and start Excel comparison.'
        : isArrangement
        ? 'Failed to upload and start I/O address arrangement.'
        : isTemplate
        ? 'Failed to upload and start ABB engineering template generation.'
        : 'Failed to upload and start conversion process.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          msg = detail;
        } else if (Array.isArray(detail)) {
          msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        } else {
          msg = JSON.stringify(detail);
        }
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        msg =
          'The backend is waking up (Render free tier cold start). Please wait ~30–60 seconds and try again.';
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
