import { create } from 'zustand';
import { ProcessStatusResponse, PipelineStage } from '../types/converter';

interface ConverterState {
  stage: PipelineStage;
  conversionType: 'DB' | 'PC';
  jobId: string | null;
  selectedFiles: File[];
  statusResponse: ProcessStatusResponse | null;
  isLogModalOpen: boolean;
  logText: string;

  setStage: (stage: PipelineStage) => void;
  setConversionType: (type: 'DB' | 'PC') => void;
  setSelectedFiles: (files: File[]) => void;
  removeFile: (index: number) => void;
  setJobId: (id: string | null) => void;
  setStatusResponse: (status: ProcessStatusResponse | null) => void;
  openLogModal: (logText: string) => void;
  closeLogModal: () => void;
  resetSession: () => void;
}

export const useConverterStore = create<ConverterState>((set) => ({
  stage: 'upload',
  conversionType: 'DB',
  jobId: null,
  selectedFiles: [],
  statusResponse: null,
  isLogModalOpen: false,
  logText: '',

  setStage: (stage) => set({ stage }),
  setConversionType: (conversionType) => set({ conversionType }),
  setSelectedFiles: (selectedFiles) => set({ selectedFiles }),
  removeFile: (index) =>
    set((state) => ({
      selectedFiles: state.selectedFiles.filter((_, i) => i !== index),
    })),
  setJobId: (jobId) => set({ jobId }),
  setStatusResponse: (statusResponse) => set({ statusResponse }),
  openLogModal: (logText) => set({ isLogModalOpen: true, logText }),
  closeLogModal: () => set({ isLogModalOpen: false }),
  resetSession: () =>
    set({
      stage: 'upload',
      conversionType: 'DB',
      jobId: null,
      selectedFiles: [],
      statusResponse: null,
      isLogModalOpen: false,
      logText: '',
    }),
}));
