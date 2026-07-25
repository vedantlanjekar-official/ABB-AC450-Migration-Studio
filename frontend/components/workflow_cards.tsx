'use client';

import React from 'react';
import { Upload, FileSearch, Cpu, FileSpreadsheet, Download, ChevronRight } from 'lucide-react';
import { useConverterStore } from '../store/converter_store';

const steps = [
  { id: 'upload', title: 'Upload PDF', desc: 'AC450 DB Printouts', icon: Upload },
  { id: 'parse', title: 'Parse DB Elements', desc: 'Identify Tags & Blocks', icon: FileSearch },
  { id: 'extract', title: 'Extract Parameters', desc: ':KEY VALUE Pairs', icon: Cpu },
  { id: 'generate', title: 'Generate Excel', desc: 'One Sheet Per Type', icon: FileSpreadsheet },
  { id: 'download', title: 'Download Export', desc: 'Valmet Compatible', icon: Download },
];

export function WorkflowCards() {
  const { stage, statusResponse } = useConverterStore();

  const getStepStatus = (index: number) => {
    if (stage === 'upload' && index === 0) return 'active';
    if (stage === 'processing') {
      const progress = statusResponse?.progress_percentage || 0;
      if (index === 0) return 'complete';
      if (index === 1 && progress >= 25) return 'active';
      if (index === 1 && progress > 50) return 'complete';
      if (index === 2 && progress >= 50) return 'active';
      if (index === 2 && progress > 80) return 'complete';
      if (index === 3 && progress >= 80) return 'active';
      if (index === 3 && progress >= 100) return 'complete';
    }
    if (stage === 'results') return 'complete';
    return 'pending';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-8">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4 font-mono">
        Conversion Pipeline Workflow
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 relative">
        {steps.map((step, idx) => {
          const status = getStepStatus(idx);
          const Icon = step.icon;

          return (
            <div key={step.id} className="relative flex flex-col items-center">
              <div
                className={`w-full flex items-center p-3 rounded-lg border transition-all ${
                  status === 'active'
                    ? 'bg-red-50/70 border-abb-red shadow-sm text-abb-red'
                    : status === 'complete'
                    ? 'bg-slate-900 border-slate-900 text-white'
                    : 'bg-slate-50 border-slate-200 text-slate-400'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded flex items-center justify-center mr-3 shrink-0 ${
                    status === 'active'
                      ? 'bg-abb-red text-white'
                      : status === 'complete'
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-bold truncate">{step.title}</div>
                  <div className="text-[10px] opacity-75 truncate">{step.desc}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
