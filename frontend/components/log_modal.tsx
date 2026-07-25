'use client';

import React, { useState } from 'react';
import { X, Copy, Check, Terminal } from 'lucide-react';
import { useConverterStore } from '../store/converter_store';

export function LogModal() {
  const { isLogModalOpen, closeLogModal, logText } = useConverterStore();
  const [copied, setCopied] = useState(false);

  if (!isLogModalOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(logText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col text-slate-800 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 bg-slate-200/60 rounded-md text-slate-700">
              <Terminal className="w-4 h-4 text-slate-700" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900 tracking-tight">
                Execution & Parsing Log Inspector
              </h3>
              <p className="text-xs text-slate-500 font-normal">Audit report and system operation traces</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopy}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 text-xs font-medium rounded-md shadow-2xs transition"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
              <span>{copied ? 'Copied' : 'Copy Log'}</span>
            </button>
            <button
              onClick={closeLogModal}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-100 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto font-mono text-xs bg-slate-50/50 text-slate-700 border-t border-slate-100 leading-relaxed whitespace-pre-wrap select-text">
          {logText || 'No log text available.'}
        </div>
      </div>
    </div>
  );
}
