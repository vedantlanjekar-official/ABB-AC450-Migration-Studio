'use client'

import React from 'react'
import { useConverterStore } from '../store/converter_store'
import { useStatusPolling } from '../hooks/use_status_polling'
import { Loader2, FileSearch, ShieldCheck, Cpu, Database, Network, Box, FileSpreadsheet, CheckCircle2, Sliders, Layers } from 'lucide-react'

export const ProcessingView: React.FC = () => {
  // Activate automatic status polling
  useStatusPolling()

  const { statusResponse } = useConverterStore()

  const progress = statusResponse?.progress_percentage || 10
  const phase = statusResponse?.current_phase || 'Executing 10-Stage Compiler Parser Engine...'
  const message = statusResponse?.message || 'Reading uploaded PDF document(s)...'

  // 10 distinct, uncombined stages using Valmet green color scheme
  const stages = [
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

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="text-center pb-4">
          <div className="mx-auto w-16 h-16 rounded-full bg-valmet-lightgreen text-valmet-green flex items-center justify-center mb-4 shadow-xs">
            <Loader2 className="w-8 h-8 text-valmet-green animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Executing 10-Stage Compiler Parser Engine
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 font-medium">{phase}</p>
        </div>

        <div className="space-y-6 pt-2">
          {/* Progress Bar with Valmet Green */}
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

          {/* 10 Separate Compiler Pipeline Stages */}
          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
              Compiler Pipeline Stages (10 Separate Stages)
            </h4>
            <div className="grid grid-cols-1 gap-2">
              {stages.map((stg) => {
                const Icon = stg.icon
                const isDone = progress >= stg.minProgress
                const isActive = progress >= stg.minProgress - 9 && !isDone

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
