import axios from 'axios';
import { FileUploadResponse, ProcessStatusResponse } from '../types/converter';

const DEFAULT_PRODUCTION_API_URL = 'https://abb-ac450-migration-studio-backend.onrender.com/api';

function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.startsWith('http')) {
    return envUrl;
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return DEFAULT_PRODUCTION_API_URL;
  }
  return envUrl || 'http://localhost:8000/api';
}

export const apiClient = {
  async uploadFiles(files: File[]): Promise<FileUploadResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post<FileUploadResponse>(
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
    await axios.post(`${baseUrl}/process`, {
      job_id: jobId,
      conversion_type: conversionType,
    });
  },

  async getJobStatus(jobId: string): Promise<ProcessStatusResponse> {
    const baseUrl = getApiBaseUrl();
    const response = await axios.get<ProcessStatusResponse>(
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
    const response = await axios.get<string>(`${baseUrl}/logs/${jobId}`, {
      responseType: 'text',
    });
    return response.data;
  },
};

