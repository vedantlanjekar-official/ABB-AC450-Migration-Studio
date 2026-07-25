import axios from 'axios';
import { FileUploadResponse, ProcessStatusResponse } from '../types/converter';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

export const apiClient = {
  async uploadFiles(files: File[]): Promise<FileUploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post<FileUploadResponse>(
      `${API_BASE_URL}/upload`,
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
    await axios.post(`${API_BASE_URL}/process`, {
      job_id: jobId,
      conversion_type: conversionType,
    });
  },

  async getJobStatus(jobId: string): Promise<ProcessStatusResponse> {
    const response = await axios.get<ProcessStatusResponse>(
      `${API_BASE_URL}/status/${jobId}`
    );
    return response.data;
  },

  getDownloadUrl(jobId: string): string {
    return `${API_BASE_URL}/download/${jobId}`;
  },

  async getJobLog(jobId: string): Promise<string> {
    const response = await axios.get<string>(`${API_BASE_URL}/logs/${jobId}`, {
      responseType: 'text',
    });
    return response.data;
  },
};
