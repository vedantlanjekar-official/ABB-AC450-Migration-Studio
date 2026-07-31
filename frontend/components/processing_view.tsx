'use client'

import React from 'react'
import { useConverterStore } from '../store/converter_store'
import { useStatusPolling } from '../hooks/use_status_polling'
import {
  Loader2,
  FileSearch,
  ShieldCheck,
  Cpu,
  Database,
  Network,
  Box,
  FileSpreadsheet,
  CheckCircle2,
  Sliders,
  Layers,
  GitCompare,
  Search,
  LayoutTemplate,
} from 'lucide-react'

export const ProcessingView: React.FC = () => {
  useStatusPolling()

  const { statusResponse, conversionType } = useConverterStore()

  const activeType = statusResponse?.conversion_type || conversionType
  const isCompare = activeType === 'COMPARE'
  const isArrangement = activeType === 'IO_ARRANGE'
  const isTemplate = activeType === 'ENG_TEMPLATE'

  const progress = statusResponse?.progress_percentage || 10
  const phase =
    statusResponse?.current_phase ||
    (isTemplate
      ? 'Mapping clubbed records into ABB template...'
      : isArrangement
      ? 'Generating paired ABB I/O addresses...'
      : isCompare
      ? 'Excel Comparison & Validation...'
      : 'Executing 10-Stage Compiler Parser Engine...')
  const message =
    statusResponse?.message ||
    (isTemplate
      ? 'Reading generated engineering workbook...'
      : isArrangement
      ? 'Reading generated engineering workbook...'
      : isCompare
      ? 'Reading uploaded Excel worksheets...'
      : 'Reading uploaded PDF document(s)...')

  const pdfStages = [
    { num: 1, title: 'Stage 1: PDF Document Extraction & Page Loading', icon: FileSearch, minProgress: 10 },
    { num: 2, title: 'Stage 2: Header & Footer Noise Filtering', icon: ShieldCheck, minProgress: 20 },
    { num: 3, title: 'Stage 3: Multi-Page Document Merging & Alignment', icon: Network, minProgress: 30 },
    { num: 4, title: 'Stage 4: Lexical Tokenization & Line Parsing', icon: Cpu, minProgress: 40 },
    { num: 5, title: 'Stage 5: Default Section Library Construction', icon: Database, minProgress: 50 },
    { num: 6, title: 'Stage 6: Multi-Block Inheritance Profiling', icon: Box, minProgress: 60 },
    { num: 7, title: 'Stage 7: Object Boundary & Parameter Extraction', icon: Sliders, minProgress: 70 },
    { num: 8, title: 'Stage 8: Family Default Inheritance Merging', icon: Layers, minProgress: 80 },
    { num: 9, title: 'Stage 9: Engineering Integrity & Schema Validation', icon: ShieldCheck, minProgress: 90 },
    { num: 10, title: 'Stage 10: Valmet-Compatible Excel Workbook Generation', icon: FileSpreadsheet, minProgress: 100 },
  ]

  const compareStages = [
    { num: 1, title: 'Stage 1: Upload & Read Excel Workbooks', icon: FileSpreadsheet, minProgress: 20 },
    { num: 2, title: 'Stage 2: Locate $(DEVICETAG) in Both Files', icon: Search, minProgress: 40 },
    { num: 3, title: 'Stage 3: Extract & Deduplicate Tag Values', icon: Layers, minProgress: 55 },
    { num: 4, title: 'Stage 4: Compare Both Tag Sets', icon: GitCompare, minProgress: 70 },
    { num: 5, title: 'Stage 5: Generate Comparison_Report.xlsx', icon: FileSpreadsheet, minProgress: 100 },
  ]

  const arrangementStages = [
    { num: 1, title: 'Stage 1: Read Generated DB / PB/PC Excel', icon: FileSpreadsheet, minProgress: 25 },
    { num: 2, title: 'Stage 2: Detect Device Tag & Category Columns', icon: Search, minProgress: 45 },
    { num: 3, title: 'Stage 3: Preserve and Group Category Records', icon: Layers, minProgress: 55 },
    { num: 4, title: 'Stage 4: Generate Paired ABB Card Addresses', icon: Network, minProgress: 80 },
    { num: 5, title: 'Stage 5: Export I/O Address Arrangement', icon: FileSpreadsheet, minProgress: 100 },
  ]

  const templateStages = [
    { num: 1, title: 'Stage 1: Read Generated DB / PB/PC Excel', icon: FileSpreadsheet, minProgress: 25 },
    { num: 2, title: 'Stage 2: Detect Club Headers & Category Columns', icon: Search, minProgress: 40 },
    { num: 3, title: 'Stage 3: Collapse Adjacent Compatible Clubs', icon: LayoutTemplate, minProgress: 70 },
    { num: 4, title: 'Stage 4: Export ABB_Engineering_Template.xlsx', icon: FileSpreadsheet, minProgress: 100 },
  ]

  const stages = isTemplate
    ? templateStages
    : isArrangement
    ? arrangementStages
    : isCompare
    ? compareStages
    : pdfStages

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="text-center pb-4">
          <div className="mx-auto w-16 h-16 rounded-full bg-valmet-lightgreen text-valmet-green flex items-center justify-center mb-4 shadow-xs">
            <Loader2 className="w-8 h-8 text-valmet-green animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            {isTemplate
              ? 'ABB Engineering Template Generator'
              : isArrangement
              ? 'I/O Address Arrangement Generator'
              : isCompare
              ? 'Excel Comparison & Validation'
              : 'Executing 10-Stage Compiler Parser Engine'}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 font-medium">{phase}</p>
        </div>

        <div className="space-y-6 pt-2">
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-semibold text-slate-700 uppercase tracking-wider font-mono">
              <span className="truncate pr-2">{message}</span>
              <span className="text-valmet-green">{progress}%</span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden border border-slate-200">
              <div
                className="h-full bg-valmet-green transition-all duration-300 rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
              {isTemplate
                ? 'Engineering Template Pipeline Stages'
                : isArrangement
                ? 'I/O Arrangement Pipeline Stages'
                : isCompare
                ? 'Comparison Pipeline Stages'
                : 'Compiler Pipeline Stages (10 Separate Stages)'}
            </h4>
            <div className="grid grid-cols-1 gap-2">
              {stages.map((stg) => {
                const Icon = stg.icon
                const isDone = progress >= stg.minProgress
                const prev = stages.find((s) => s.num === stg.num - 1)
                const isActive =
                  !isDone && progress >= (prev?.minProgress ?? 0)

                return (
                  <div
                    key={stg.num}
                    className={`flex items-center gap-3 p-3 rounded-xl border text-xs sm:text-sm transition-all duration-300 ${
                      isDone
                        ? 'bg-valmet-lightgreen/70 border-valmet-green/40 text-valmet-darkgreen font-medium'
                        : isActive
                        ? 'bg-emerald-50 border-valmet-green text-valmet-green font-semibold shadow-xs'
                        : 'bg-slate-50/80 border-slate-200 text-slate-400'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-valmet-green shrink-0" />
                    ) : isActive ? (
                      <Loader2 className="w-4 h-4 text-valmet-green animate-spin shrink-0" />
                    ) : (
                      <Icon className="w-4 h-4 shrink-0 text-slate-400" />
                    )}
                    <span className="flex-1 truncate">{stg.title}</span>
                    <span
                      className={`text-[11px] font-semibold px-2.5 py-0.5 rounded ${
                        isDone
                          ? 'bg-valmet-green text-white'
                          : isActive
                          ? 'bg-emerald-100 text-valmet-darkgreen'
                          : 'bg-white border border-slate-200 text-slate-400'
                      }`}
                    >
                      {isDone ? 'Completed' : isActive ? 'Processing' : 'Pending'}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
