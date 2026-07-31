import { create } from 'zustand';
import { ProcessStatusResponse, PipelineStage, ConversionType } from '../types/converter';

interface ConverterState {
  stage: PipelineStage;
  conversionType: ConversionType;
  jobId: string | null;
  selectedFiles: File[];
  /** Excel Comparison: Worksheet 1 (Device Tag) */
  compareFile1: File | null;
  /** Excel Comparison: Worksheet 2 (NAME) */
  compareFile2: File | null;
  /** I/O Address Arrangement: generated DB or PC workbook */
  arrangementFile: File | null;
  /** ABB Engineering Template: generated DB or PC workbook */
  templateFile: File | null;
  statusResponse: ProcessStatusResponse | null;
  isLogModalOpen: boolean;
  logText: string;

  setStage: (stage: PipelineStage) => void;
  setConversionType: (type: ConversionType) => void;
  setSelectedFiles: (files: File[]) => void;
  removeFile: (index: number) => void;
  setCompareFile1: (file: File | null) => void;
  setCompareFile2: (file: File | null) => void;
  setArrangementFile: (file: File | null) => void;
  setTemplateFile: (file: File | null) => void;
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
  compareFile1: null,
  compareFile2: null,
  arrangementFile: null,
  templateFile: null,
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
  setCompareFile1: (compareFile1) => set({ compareFile1 }),
  setCompareFile2: (compareFile2) => set({ compareFile2 }),
  setArrangementFile: (arrangementFile) => set({ arrangementFile }),
  setTemplateFile: (templateFile) => set({ templateFile }),
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
      compareFile1: null,
      compareFile2: null,
      arrangementFile: null,
      templateFile: null,
      statusResponse: null,
      isLogModalOpen: false,
      logText: '',
    }),
}));
