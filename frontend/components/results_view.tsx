'use client';

import React, { useState } from 'react';
import { useConverterStore } from '../store/converter_store';
import {
  Download,
  Layers,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Search,
  Table as TableIcon,
  Cpu,
  Sliders,
  Eye,
  ShieldCheck,
  Clock,
  FileSpreadsheet,
  GitCompare,
  LayoutTemplate,
} from 'lucide-react';
import { apiClient } from '../services/api_client';

export function ResultsView() {
  const { statusResponse, resetSession, openLogModal } = useConverterStore();
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loadingLog, setLoadingLog] = useState<boolean>(false);

  if (!statusResponse) return null;

  const {
    job_id,
    status,
    conversion_type = 'DB',
    total_objects,
    default_sections_found,
    hardware_default_blocks,
    software_default_blocks,
    merged_profiles_created,
    parameters_filled_from_defaults,
    object_overrides,
    ignored_header_footer_lines,
    ai_count = 0,
    ao_count = 0,
    di_count = 0,
    do_count = 0,
    duplicate_records = 0,
    processing_time_seconds,
    worksheet1_records = 0,
    worksheet2_records = 0,
    matched_records = 0,
    unmatched_records = 0,
    detected_element_types,
    generated_sheets,
    preview_data,
    warnings,
  } = statusResponse;

  const activeSheet = selectedSheet || generated_sheets[0] || '';
  const sheetRows = preview_data[activeSheet] || [];

  // Filter rows based on search
  const filteredRows = sheetRows.filter((row) =>
    Object.values(row).some((val) =>
      String(val ?? '').toLowerCase().includes(searchQuery.toLowerCase())
    )
  );

  const downloadUrl = apiClient.getDownloadUrl(job_id);

  const handleFetchLogs = async () => {
    try {
      setLoadingLog(true);
      const logs = await apiClient.getJobLog(job_id);
      openLogModal(logs);
    } catch {
      openLogModal('Execution logs for this job are being processed...');
    } finally {
      setLoadingLog(false);
    }
  };

  const isPC = conversion_type === 'PC';
  const isCompare = conversion_type === 'COMPARE';
  const isArrangement = conversion_type === 'IO_ARRANGE';
  const isTemplate = conversion_type === 'ENG_TEMPLATE';
  const isFailed = status === 'failed';

  return (
    <div className="space-y-6">
      {/* Light Professional Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-white border border-slate-200 rounded-2xl shadow-xs">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-xl border ${
            isFailed
              ? 'bg-red-50 text-red-600 border-red-200'
              : 'bg-valmet-lightgreen text-valmet-green border-valmet-green/30'
          }`}>
            {isFailed ? <AlertTriangle className="w-7 h-7" /> : <CheckCircle2 className="w-7 h-7" />}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              {isFailed
                ? isTemplate
                  ? 'ABB Engineering Template Failed'
                  : isArrangement
                  ? 'I/O Address Arrangement Failed'
                  : isCompare
                  ? 'Excel Comparison Failed'
                  : 'Conversion Failed'
                : isTemplate
                ? 'ABB Engineering Template Complete'
                : isArrangement
                ? 'I/O Address Arrangement Complete'
                : isCompare
                ? 'Excel Comparison Complete'
                : isPC
                ? 'PC Element IO Extraction Complete'
                : 'DB Element Conversion Complete'}
            </h2>
            {isFailed && statusResponse.message && (
              <p className="text-sm text-red-600 mt-1">{statusResponse.message}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap justify-end">
          <button
            onClick={handleFetchLogs}
            disabled={loadingLog}
            className="flex items-center gap-2 px-4 py-2.5 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-xl text-xs font-bold transition-all shadow-xs disabled:opacity-50"
          >
            <Eye className="w-4 h-4 text-slate-400" />
            <span>{loadingLog ? 'Loading Log...' : 'View Execution Log'}</span>
          </button>

          {!isFailed && (
            <a
              href={downloadUrl}
              download={
                isTemplate
                  ? 'ABB_Engineering_Template.xlsx'
                  : isArrangement
                  ? 'IO_Address_Arrangement.xlsx'
                  : isCompare
                  ? 'Comparison_Report.xlsx'
                  : undefined
              }
              className="flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-valmet-lightgreen/50 text-valmet-green border border-valmet-green rounded-xl text-xs font-extrabold transition-all shadow-xs active:scale-95 group"
            >
              <FileSpreadsheet className="w-4 h-4 text-valmet-green group-hover:scale-110 transition-transform" />
              <span>
                {isTemplate
                  ? 'Download ABB Engineering Template'
                  : isArrangement
                  ? 'Download I/O Address Arrangement'
                  : isCompare
                  ? 'Download Comparison_Report.xlsx'
                  : 'Download Excel (.xlsx)'}
              </span>
            </a>
          )}

          <button
            onClick={resetSession}
            className="p-2.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-all border border-slate-200"
            title="Start Another Job"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Metrics Panel */}
      {!isFailed && (isTemplate ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <LayoutTemplate className="w-3.5 h-3.5 text-valmet-green" />
              <span>Template Rows</span>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {(total_objects || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">ABB engineering rows</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Paired Clubs</span>
            </div>
            <div className="text-xl font-bold text-blue-600 font-mono">
              {(matched_records || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Adjacent compatible pairs</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <TableIcon className="w-3.5 h-3.5 text-amber-600" />
              <span>Singleton Rows</span>
            </div>
            <div className="text-xl font-bold text-amber-600 font-mono">
              {(unmatched_records || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Single-slot template rows</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Clock className="w-3.5 h-3.5 text-valmet-green" />
              <span>Processing Time</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {processing_time_seconds || 0}s
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">No re-clubbing performed</div>
          </div>
        </div>
      ) : isArrangement ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Layers className="w-3.5 h-3.5 text-valmet-green" />
              <span>Records Arranged</span>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {(total_objects || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Device Tags preserved</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <FileSpreadsheet className="w-3.5 h-3.5 text-blue-600" />
              <span>Category Sheets</span>
            </div>
            <div className="text-xl font-bold text-blue-600 font-mono">
              {generated_sheets.length}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {detected_element_types.map((item) => `${item.element_type}: ${item.count}`).join(' · ')}
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Clock className="w-3.5 h-3.5 text-valmet-green" />
              <span>Processing Time</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {processing_time_seconds || 0}s
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Paired ABB card layout</div>
          </div>
        </div>
      ) : isCompare ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <FileSpreadsheet className="w-3.5 h-3.5 text-valmet-green" />
              <span>Worksheet 1 Records</span>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {(worksheet1_records || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">$(DEVICETAG) values</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Worksheet 2 Records</span>
            </div>
            <div className="text-xl font-bold text-blue-600 font-mono">
              {(worksheet2_records || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">$(DEVICETAG) values</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-valmet-green" />
              <span>Matched Records</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {(matched_records || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Present in both files</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <GitCompare className="w-3.5 h-3.5 text-amber-600" />
              <span>Unmatched Records</span>
            </div>
            <div className="text-xl font-bold text-amber-600 font-mono">
              {(unmatched_records || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Unique to either source</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Clock className="w-3.5 h-3.5 text-valmet-green" />
              <span>Processing Time</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {processing_time_seconds || 0}s
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Comparison runtime</div>
          </div>
        </div>
      ) : isPC ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Cpu className="w-3.5 h-3.5 text-valmet-green" />
              <span>Total IO Points</span>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {(total_objects || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">PC References</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Analog Inputs</span>
            </div>
            <div className="text-xl font-bold text-blue-600 font-mono">
              {(ai_count || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">AI / AI800 Points</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Sliders className="w-3.5 h-3.5 text-valmet-green" />
              <span>Analog Outputs</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {(ao_count || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">AO / AO800 Points</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
              <span>Digital Inputs</span>
            </div>
            <div className="text-xl font-bold text-purple-600 font-mono">
              {(di_count || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">DI / DI800 Points</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <TableIcon className="w-3.5 h-3.5 text-amber-600" />
              <span>Digital Outputs</span>
            </div>
            <div className="text-xl font-bold text-amber-600 font-mono">
              {(do_count || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">DO / DO800 Points</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Clock className="w-3.5 h-3.5 text-valmet-green" />
              <span>Processing Time</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {processing_time_seconds || 0}s
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {duplicate_records || 0} Duplicates Removed
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Layers className="w-3.5 h-3.5 text-valmet-green" />
              <span>Total Objects</span>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {(total_objects || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">DB Elements Extracted</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              <span>Default Blocks</span>
            </div>
            <div className="text-xl font-bold text-indigo-600 font-mono">
              {default_sections_found || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {hardware_default_blocks || 0} HW / {software_default_blocks || 0} SW
            </div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Cpu className="w-3.5 h-3.5 text-valmet-green" />
              <span>Merged Profiles</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {merged_profiles_created || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Layered AST Families</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
              <span>Inherited Params</span>
            </div>
            <div className="text-xl font-bold text-purple-600 font-mono">
              {(parameters_filled_from_defaults || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Default Values Filled</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-amber-600" />
              <span>Explicit Overrides</span>
            </div>
            <div className="text-xl font-bold text-amber-600 font-mono">
              {(object_overrides || 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Object Values Preserved</div>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Clock className="w-3.5 h-3.5 text-valmet-green" />
              <span>Processing Time</span>
            </div>
            <div className="text-xl font-bold text-valmet-green font-mono">
              {processing_time_seconds || 0}s
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {ignored_header_footer_lines || 0} Lines Cleaned
            </div>
          </div>
        </div>
      ))}

      {/* Compiler Errors */}
      {statusResponse.errors && statusResponse.errors.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800">
          <div className="flex items-center gap-2 text-red-900 text-xs font-bold mb-2">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <span>Conversion Errors ({statusResponse.errors.length})</span>
          </div>
          <ul className="text-xs text-red-700 space-y-1 max-h-28 overflow-y-auto">
            {statusResponse.errors.map((entry, idx) => (
              <li key={idx} className="flex items-start gap-1.5 font-mono">
                <span className="text-red-500">•</span>
                <span>{entry}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Compiler Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800">
          <div className="flex items-center gap-2 text-amber-900 text-xs font-bold mb-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Compiler Warnings ({warnings.length})</span>
          </div>
          <ul className="text-xs text-amber-700 space-y-1 max-h-28 overflow-y-auto">
            {warnings.map((w, idx) => (
              <li key={idx} className="flex items-start gap-1.5 font-mono">
                <span className="text-amber-500">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Excel Sheet Style Preview Table Component */}
      {!isFailed && (
      <div className="bg-white border border-slate-300 rounded-xl shadow-sm overflow-hidden">
        {/* Ribbon / Tab Header */}
        <div className="bg-slate-100 border-b border-slate-300 p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            <span className="text-xs font-bold text-slate-600 mr-2 flex items-center gap-1 shrink-0 font-mono">
              <FileSpreadsheet className="w-4 h-4 text-valmet-green" />
              Worksheets:
            </span>
            {generated_sheets.map((sheetName) => (
              <button
                key={sheetName}
                onClick={() => setSelectedSheet(sheetName)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                  activeSheet === sheetName
                    ? 'bg-valmet-green text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-200 border border-slate-300'
                }`}
              >
                <span>{sheetName}</span>
                <span className={`px-1.5 py-0.2 rounded text-[10px] ${
                  activeSheet === sheetName ? 'bg-valmet-darkgreen text-white' : 'bg-slate-100 text-slate-500'
                }`}>
                  {(preview_data[sheetName] || []).length}
                </span>
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search in Excel sheet..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-300 rounded-md text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-valmet-green transition-colors"
            />
          </div>
        </div>

        {/* Excel Spreadsheet Table Grid */}
        <div className="overflow-x-auto max-h-[500px]">
          {filteredRows.length > 0 ? (
            <table className="w-full text-left text-xs border-collapse font-sans">
              <thead>
                <tr className="bg-slate-200 text-slate-800 font-bold border-b border-slate-300 sticky top-0 z-10">
                  <th className="px-3 py-2 border-r border-slate-300 bg-slate-300/80 text-center w-12 font-mono text-[10px] text-slate-600">
                    #
                  </th>
                  {Object.keys(filteredRows[0]).map((col) => (
                    <th key={col} className="px-3.5 py-2 border-r border-slate-300 whitespace-nowrap font-semibold">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-800 bg-white">
                {filteredRows.map((row, rIdx) => (
                  <tr
                    key={rIdx}
                    className="hover:bg-emerald-50/50 transition-colors font-mono text-[11px] odd:bg-slate-50/60"
                  >
                    <td className="px-3 py-2 border-r border-slate-200 text-center font-mono text-[10px] text-slate-400 bg-slate-100/50">
                      {rIdx + 1}
                    </td>
                    {Object.entries(row).map(([col, val], cIdx) => (
                      <td
                        key={cIdx}
                        className={`px-3.5 py-2 border-r border-slate-200 whitespace-nowrap ${
                          col === 'Tag' || col === 'Loop Tag'
                            ? 'font-bold text-valmet-darkgreen bg-valmet-lightgreen/40'
                            : col === 'Device Tag' || col === '$(DEVICETAG)'
                            ? 'font-bold text-slate-900'
                            : 'text-slate-700'
                        }`}
                      >
                        {String(val ?? '') || '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs">
              No matching records found in worksheet '{activeSheet}'.
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  );
}
