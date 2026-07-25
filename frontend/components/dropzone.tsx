'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Trash2, AlertCircle, ArrowRight, Cpu, Layers } from 'lucide-react';
import { useConverterStore } from '../store/converter_store';
import { useFileUpload } from '../hooks/use_file_upload';
import { formatBytes } from '../utils/formatters';

export function Dropzone() {
  const { selectedFiles, setSelectedFiles, removeFile, conversionType, setConversionType } = useConverterStore();
  const { startConversion, isUploading, error } = useFileUpload();
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const pdfFiles = Array.from(e.dataTransfer.files).filter((file) =>
        file.name.toLowerCase().endsWith('.pdf')
      );
      if (pdfFiles.length > 0) {
        setSelectedFiles([...selectedFiles, ...pdfFiles]);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const pdfFiles = Array.from(e.target.files).filter((file) =>
        file.name.toLowerCase().endsWith('.pdf')
      );
      setSelectedFiles([...selectedFiles, ...pdfFiles]);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 max-w-3xl mx-auto">
      {/* Mode Selector Tabs */}
      <div className="flex items-center justify-center p-1 bg-slate-100 rounded-lg max-w-md mx-auto mb-6">
          <button
            onClick={() => setConversionType('DB')}
            className={`flex-1 flex items-center justify-center space-x-2 py-2 px-4 text-xs font-bold rounded-md transition ${
              conversionType === 'DB'
                ? 'bg-white text-valmet-green shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>DB Element Listing</span>
          </button>
          <button
            onClick={() => setConversionType('PC')}
            className={`flex-1 flex items-center justify-center space-x-2 py-2 px-4 text-xs font-bold rounded-md transition ${
              conversionType === 'PC'
                ? 'bg-white text-valmet-green shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Cpu className="w-4 h-4" />
            <span>PC Element IO References</span>
          </button>
        </div>

        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-slate-900 font-sans tracking-tight">
            Upload AC450 {conversionType === 'DB' ? 'DB Element' : 'PC Element IO Reference'} PDFs
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            {conversionType === 'DB'
              ? 'Select or drag ABB Advant Controller 450 DB printout PDF files for hierarchical AST conversion'
              : 'Select or drag ABB AC450 PC Element PDF files to extract structured IO references'}
          </p>
        </div>

        {/* Dropzone Card */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center ${
            isDragOver
              ? 'border-valmet-green bg-valmet-lightgreen/50 scale-[1.01]'
              : 'border-slate-300 hover:border-valmet-green/60 hover:bg-slate-50/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />

          <div className="w-14 h-14 rounded-full bg-valmet-lightgreen text-valmet-green flex items-center justify-center mb-4 shadow-sm">
            <UploadCloud className="w-7 h-7" />
          </div>

          <div className="text-sm font-bold text-slate-800">
            Drag & Drop PDF files here, or{' '}
            <span className="text-valmet-green hover:underline">Browse Files</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Supported formats: Database Listing PDF, PC Element PDF (up to 100MB each)
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Selected File List */}
        {selectedFiles.length > 0 && (
          <div className="mt-6 border-t border-slate-200 pt-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono">
                Selected PDF Files ({selectedFiles.length})
              </span>
              <button
                onClick={() => setSelectedFiles([])}
                className="text-xs text-slate-400 hover:text-red-600 transition"
              >
                Clear All
              </button>
            </div>

            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {selectedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs"
                >
                  <div className="flex items-center space-x-2.5 min-w-0">
                    <FileText className="w-4 h-4 text-valmet-green shrink-0" />
                    <span className="font-medium text-slate-800 truncate">
                      {file.name}
                    </span>
                    <span className="text-slate-400 shrink-0">
                      ({formatBytes(file.size)})
                    </span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(idx);
                    }}
                    className="p-1 text-slate-400 hover:text-red-600 hover:bg-slate-200 rounded transition"
                    title="Remove file"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={startConversion}
                disabled={isUploading}
                className="w-full sm:w-auto px-6 py-3 bg-valmet-green hover:bg-valmet-darkgreen text-white text-sm font-bold rounded-lg shadow transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <span>{isUploading ? 'Uploading PDF...' : `Start ${conversionType} Conversion`}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
    </div>
  );
}
