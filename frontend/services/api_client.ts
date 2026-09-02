import axios from 'axios';
import { FileUploadResponse, ProcessStatusResponse, ConversionType } from '../types/converter';

/** Fallback when env/rewrite is missing. Keep in sync with render.yaml service name. */
const PRODUCTION_API_URL = 'https://valmet-abb-ac450-api.onrender.com/api';
const LOCAL_API_URL = 'http://127.0.0.1:8002/api';

function isBrowserLocalHost(): boolean {
  if (typeof window === 'undefined') return false;
  const hostname = window.location.hostname;
  return hostname === 'localhost' || hostname === '127.0.0.1';
}

function isLocalApiUrl(url: string): boolean {
  return url.includes('localhost') || url.includes('127.0.0.1');
}

/**
 * Browser on Vercel uses same-origin `/api` (Next.js rewrite → Render).
 * That avoids cross-origin "Network Error" when the API host is cold or CORS fails.
 * Localhost still calls the FastAPI port directly.
 */
function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;

  if (typeof window !== 'undefined') {
    if (isBrowserLocalHost()) {
      return envUrl && envUrl.startsWith('http') ? envUrl : LOCAL_API_URL;
    }
    return '/api';
  }

  if (envUrl && envUrl.startsWith('http') && !isLocalApiUrl(envUrl)) {
    return envUrl;
  }

  return process.env.NODE_ENV === 'production' ? PRODUCTION_API_URL : LOCAL_API_URL;
}

const axiosClient = axios.create({
  timeout: 300000,
});

export const apiClient = {
  async uploadFiles(files: File[]): Promise<FileUploadResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axiosClient.post<FileUploadResponse>(
      `${baseUrl}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async triggerProcess(jobId: string, conversionType: ConversionType = 'DB'): Promise<void> {
    const baseUrl = getApiBaseUrl();
    await axiosClient.post(`${baseUrl}/process`, {
      job_id: jobId,
      conversion_type: conversionType,
    });
  },

  async getJobStatus(jobId: string): Promise<ProcessStatusResponse> {
    const baseUrl = getApiBaseUrl();
    const response = await axiosClient.get<ProcessStatusResponse>(
      `${baseUrl}/status/${jobId}`
    );
    return response.data;
  },

  getDownloadUrl(jobId: string): string {
    const baseUrl = getApiBaseUrl();
    return `${baseUrl}/download/${jobId}`;
  },

  async getJobLog(jobId: string): Promise<string> {
    const baseUrl = getApiBaseUrl();
    const response = await axiosClient.get<string>(`${baseUrl}/logs/${jobId}`, {
      responseType: 'text',
    });
    return response.data;
  },
};
