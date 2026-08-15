'use client';

import React, { useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  Cpu,
  FileSpreadsheet,
  FileText,
  GitCompare,
  Layers,
  LayoutTemplate,
  Trash2,
  UploadCloud,
} from 'lucide-react';

import { useFileUpload } from '../hooks/use_file_upload';
import { useConverterStore } from '../store/converter_store';
import { ConversionType } from '../types/converter';
import { formatBytes } from '../utils/formatters';

type ServiceOption = {
  type: ConversionType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

type WorkflowUploadBoxProps = {
  title: string;
  description: string;
  services: ServiceOption[];
  tone: 'slate' | 'emerald';
};

const DATA_SERVICES: ServiceOption[] = [
  { type: 'DB', label: 'DB Element Converter', icon: Layers },
  { type: 'PC', label: 'PC Element Converter', icon: Cpu },
  { type: 'COMPARE', label: 'Engineering Tag Comparator', icon: GitCompare },
];

const DELIVERABLE_SERVICES: ServiceOption[] = [
  { type: 'IO_ARRANGE', label: 'I/O Address Generator', icon: FileSpreadsheet },
  {
    type: 'ENG_TEMPLATE',
    label: 'ABB Engineering Template Generator',
    icon: LayoutTemplate,
  },
];

const WORKFLOW_COPY: Record<
  ConversionType,
  { title: string; description: string; action: string }
> = {
  DB: {
    title: 'DB Element Converter',
    description:
      'Upload ABB Advant Controller 450 DB printout PDF or BAX files for structured Excel conversion.',
    action: 'Start DB Conversion',
  },
  PC: {
    title: 'PC Element Converter',
    description:
      'Upload ABB AC450 PC Element PDF or AAX files to extract structured hardwired I/O references.',
    action: 'Start PC Conversion',
  },
  COMPARE: {
    title: 'Engineering Tag Comparator',
    description:
      'Upload two Excel files containing $(DEVICETAG) to identify matched and unmatched tags.',
    action: 'Start Engineering Tag Comparison',
  },
  IO_ARRANGE: {
    title: 'I/O Address Generator',
    description:
      'Upload one generated DB or PC workbook to create paired ABB address worksheets.',
    action: 'Generate I/O Addresses',
  },
  ENG_TEMPLATE: {
    title: 'ABB Engineering Template Generator',
    description:
      'Upload one generated DB or PC workbook to map adjacent clubs into ABB template rows.',
    action: 'Generate ABB Engineering Template',
  },
};

function isPdfFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.pdf');
}

function isBaxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.bax');
}

function isAaxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.aax');
}

function isDbSourceFile(file: File): boolean {
  return isPdfFile(file) || isBaxFile(file);
}

function isPcSourceFile(file: File): boolean {
  return isPdfFile(file) || isAaxFile(file);
}

function isExcelFile(file: File, allowLegacy = false): boolean {
  const name = file.name.toLowerCase();
  return (
    name.endsWith('.xlsx') ||
    name.endsWith('.xlsm') ||
    (allowLegacy && name.endsWith('.xls'))
  );
}

function WorkflowUploadBox({
  title,
  description,
  services,
  tone,
}: WorkflowUploadBoxProps) {
  const [activeType, setActiveType] = useState<ConversionType>(services[0].type);
  const [isDragOver, setIsDragOver] = useState(false);
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const compare1Ref = useRef<HTMLInputElement>(null);
  const compare2Ref = useRef<HTMLInputElement>(null);
  const arrangementRef = useRef<HTMLInputElement>(null);
  const templateRef = useRef<HTMLInputElement>(null);

  const {
    selectedFiles,
    setSelectedFiles,
    removeFile,
    setConversionType,
    compareFile1,
    compareFile2,
    setCompareFile1,
    setCompareFile2,
    arrangementFile,
    setArrangementFile,
    templateFile,
    setTemplateFile,
  } = useConverterStore();
  const { startConversion, isUploading, error } = useFileUpload();

  const copy = WORKFLOW_COPY[activeType];
  const isDbWorkflow = activeType === 'DB';
  const isPcWorkflow = activeType === 'PC';
  const isPdfWorkflow = isDbWorkflow || isPcWorkflow;
  const isCompare = activeType === 'COMPARE';
  const isArrangement = activeType === 'IO_ARRANGE';
  const isTemplate = activeType === 'ENG_TEMPLATE';

  const selectService = (type: ConversionType) => {
    setActiveType(type);
    setConversionType(type);
  };

  const beginConversion = () => {
    setConversionType(activeType);
    void startConversion(activeType);
  };

  const handleDocumentFiles = (files: File[]) => {
    const accepted = isDbWorkflow
      ? files.filter(isDbSourceFile)
      : isPcWorkflow
      ? files.filter(isPcSourceFile)
      : files.filter(isPdfFile);
    if (accepted.length) {
      setSelectedFiles([...selectedFiles, ...accepted]);
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);
    if (isPdfWorkflow) {
      handleDocumentFiles(Array.from(event.dataTransfer.files || []));
    }
  };

  const handleCompareSelect = (
    event: React.ChangeEvent<HTMLInputElement>,
    slot: 1 | 2
  ) => {
    const file = event.target.files?.[0];
    if (file && isExcelFile(file, true)) {
      if (slot === 1) setCompareFile1(file);
      else setCompareFile2(file);
    }
    event.target.value = '';
  };

  const renderError = () =>
    error ? (
      <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
        <span>{error}</span>
      </div>
    ) : null;

  const renderExcelPicker = (
    file: File | null,
    setFile: (file: File | null) => void,
    inputRef: React.RefObject<HTMLInputElement>,
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => void,
    label: string
  ) => (
    <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3 mb-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-600">
          {label}
        </p>
        {file && (
          <button
            type="button"
            onClick={() => setFile(null)}
            className="text-xs text-slate-400 hover:text-red-600 transition"
          >
            Remove
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xlsm,.xls"
        onChange={onChange}
        className="hidden"
      />
      {file ? (
        <div className="flex items-center gap-3 rounded-md border border-emerald-200 bg-white p-3.5 text-xs shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-emerald-50">
            <FileSpreadsheet className="w-4 h-4 text-valmet-green shrink-0" />
          </div>
          <span className="font-medium text-slate-800 truncate">{file.name}</span>
          <span className="text-slate-400 shrink-0">({formatBytes(file.size)})</span>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="group w-full rounded-lg border border-dashed border-slate-300 bg-white p-7 text-center hover:border-valmet-green/60 hover:bg-emerald-50/30 transition"
        >
          <span className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full border border-emerald-100 bg-emerald-50 text-valmet-green group-hover:bg-emerald-100 transition">
            <UploadCloud className="w-5 h-5" />
          </span>
          <span className="block text-xs font-bold text-slate-800">
            Upload {label}
          </span>
          <span className="mt-1 block text-[11px] text-slate-400">
            Select an Excel workbook from your computer
          </span>
        </button>
      )}
    </div>
  );

  const canStart =
    (isPdfWorkflow && selectedFiles.length > 0) ||
    (isCompare && Boolean(compareFile1 && compareFile2)) ||
    (isArrangement && Boolean(arrangementFile)) ||
    (isTemplate && Boolean(templateFile));

  return (
    <section
      className="rounded-xl border border-slate-200 bg-white shadow-[0_8px_30px_rgba(15,23,42,0.06)] overflow-hidden"
    >
      <div
        className={`p-5 sm:p-6 border-b border-slate-200 ${
          tone === 'emerald' ? 'border-t-2 border-t-valmet-green' : 'border-t-2 border-t-slate-700'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="flex items-start gap-3">
            <span
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-xs font-extrabold ${
                tone === 'emerald'
                  ? 'bg-emerald-50 text-valmet-green'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {tone === 'emerald' ? '02' : '01'}
            </span>
            <div>
              <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-slate-800">
                {title}
              </p>
              <p className="text-xs text-slate-500 mt-1">{description}</p>
            </div>
          </div>
          <span className="w-fit rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {services.length} services
          </span>
        </div>
        <div
          className={`grid grid-cols-1 gap-2 mt-5 rounded-lg bg-slate-100/80 p-1.5 ${
            services.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'
          }`}
        >
          {services.map(({ type, label, icon: Icon }) => (
            <button
              key={type}
              type="button"
              onClick={() => selectService(type)}
              className={`min-h-14 flex items-center justify-start gap-3 rounded-md border px-3.5 py-2.5 text-xs font-bold transition ${
                activeType === type
                  ? 'bg-white text-slate-900 border-slate-200 shadow-sm'
                  : 'bg-transparent text-slate-500 border-transparent hover:bg-white/70 hover:text-slate-800'
              }`}
            >
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
                  activeType === type
                    ? 'bg-emerald-50 text-valmet-green'
                    : 'bg-white text-slate-500'
                }`}
              >
                <Icon className="w-4 h-4" />
              </span>
              <span className="text-left leading-tight">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-5 sm:p-7 lg:p-8">
        <div className="mb-6 border-l-2 border-valmet-green pl-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-valmet-green">
            Selected workflow
          </p>
          <h2 className="mt-1 text-lg sm:text-xl font-bold text-slate-900 tracking-tight">
            {copy.title}
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-3xl">{copy.description}</p>
        </div>

        {isPdfWorkflow && (
          <div className="space-y-4">
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => pdfInputRef.current?.click()}
              className={`group rounded-lg border border-dashed p-9 text-center cursor-pointer transition ${
                isDragOver
                  ? 'border-valmet-green bg-valmet-lightgreen/50'
                  : 'border-slate-300 bg-slate-50/40 hover:border-valmet-green/60 hover:bg-emerald-50/30'
              }`}
            >
              <input
                ref={pdfInputRef}
                type="file"
                accept={
                  isDbWorkflow
                    ? '.pdf,.bax,application/pdf'
                    : isPcWorkflow
                    ? '.pdf,.aax,application/pdf'
                    : '.pdf,application/pdf'
                }
                multiple
                onChange={(event) => {
                  handleDocumentFiles(Array.from(event.target.files || []));
                  event.target.value = '';
                }}
                className="hidden"
              />
              <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-emerald-100 bg-emerald-50 text-valmet-green group-hover:bg-emerald-100 transition">
                <UploadCloud className="w-6 h-6" />
              </span>
              <p className="text-sm font-bold text-slate-800">
                {isDbWorkflow
                  ? 'Drag and drop PDF or BAX files'
                  : isPcWorkflow
                  ? 'Drag and drop PDF or AAX files'
                  : 'Drag and drop PDF files'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                or <span className="font-semibold text-valmet-green">browse files</span> · up to 100MB each
              </p>
              {isDbWorkflow && (
                <p className="text-[11px] font-semibold text-slate-500 mt-2 tracking-wide">
                  Supported Formats: PDF, BAX
                </p>
              )}
              {isPcWorkflow && (
                <p className="text-[11px] font-semibold text-slate-500 mt-2 tracking-wide">
                  Supported Formats: PDF, AAX
                </p>
              )}
            </div>

            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                {selectedFiles.map((file, index) => (
                  <div
                    key={`${file.name}-${index}`}
                    className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50/70 p-3 text-xs"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-valmet-green shrink-0" />
                      <span className="font-medium text-slate-800 truncate">
                        {file.name}
                      </span>
                      <span className="text-slate-400 shrink-0">
                        ({formatBytes(file.size)})
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="p-1 text-slate-400 hover:text-red-600"
                      title="Remove file"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {renderError()}
          </div>
        )}

        {isCompare && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {renderExcelPicker(
                compareFile1,
                setCompareFile1,
                compare1Ref,
                (event) => handleCompareSelect(event, 1),
                'Excel Worksheet 1'
              )}
              {renderExcelPicker(
                compareFile2,
                setCompareFile2,
                compare2Ref,
                (event) => handleCompareSelect(event, 2),
                'Excel Worksheet 2'
              )}
            </div>
            {renderError()}
          </div>
        )}

        {isArrangement &&
          renderExcelPicker(
            arrangementFile,
            setArrangementFile,
            arrangementRef,
            (event) => {
              const file = event.target.files?.[0];
              if (file && isExcelFile(file)) setArrangementFile(file);
              event.target.value = '';
            },
            'Generated DB or PC Workbook'
          )}

        {isTemplate &&
          renderExcelPicker(
            templateFile,
            setTemplateFile,
            templateRef,
            (event) => {
              const file = event.target.files?.[0];
              if (file && isExcelFile(file)) setTemplateFile(file);
              event.target.value = '';
            },
            'Generated DB or PC Workbook'
          )}

        {(isArrangement || isTemplate) && <div className="mt-4">{renderError()}</div>}

        {canStart && (
          <div className="mt-6 flex justify-end border-t border-slate-100 pt-5">
            <button
              type="button"
              onClick={beginConversion}
              disabled={isUploading}
              className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-md bg-valmet-green px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-valmet-darkgreen transition disabled:opacity-50"
            >
              <span>{isUploading ? 'Uploading...' : copy.action}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

export function Dropzone() {
  return (
    <div className="max-w-5xl mx-auto space-y-7">
      <WorkflowUploadBox
        title="Engineering Data Processing"
        description="Extract, structure, and compare ABB AC450 engineering data."
        services={DATA_SERVICES}
        tone="slate"
      />
      <WorkflowUploadBox
        title="Engineering Deliverables"
        description="Generate structured, project-ready engineering workbooks."
        services={DELIVERABLE_SERVICES}
        tone="emerald"
      />
    </div>
  );
}
