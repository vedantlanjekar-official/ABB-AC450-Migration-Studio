import axios from 'axios';
import { FileUploadResponse, ProcessStatusResponse } from '../types/converter';

const PRODUCTION_API_URL = 'https://abb-ac450-migration-studio-backend.onrender.com/api';
const LOCAL_API_URL = 'http://127.0.0.1:8000/api';

function isLocalHost(): boolean {
  if (typeof window === 'undefined') {
    return process.env.NODE_ENV !== 'production';
  }
  const hostname = window.location.hostname;
  return hostname === 'localhost' || hostname === '127.0.0.1';
}

function isLocalApiUrl(url: string): boolean {
  return url.includes('localhost') || url.includes('127.0.0.1');
}

function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;

  if (isLocalHost()) {
    return envUrl && envUrl.startsWith('http') ? envUrl : LOCAL_API_URL;
  }

  if (envUrl && envUrl.startsWith('http') && !isLocalApiUrl(envUrl)) {
    return envUrl;
  }

  return PRODUCTION_API_URL;
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

  async triggerProcess(jobId: string, conversionType: 'DB' | 'PC' = 'DB'): Promise<void> {
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
