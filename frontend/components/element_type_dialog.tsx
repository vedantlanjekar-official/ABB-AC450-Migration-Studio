'use client';

import React, { useState } from 'react';
import { Cpu, Layers, X } from 'lucide-react';
import { ConversionType } from '../types/converter';

type ElementConversionType = Extract<ConversionType, 'DB' | 'PC'>;

type ElementTypeDialogProps = {
  open: boolean;
  isStarting?: boolean;
  onClose: () => void;
  onConfirm: (type: ElementConversionType) => void;
};

const OPTIONS: {
  type: ElementConversionType;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  {
    type: 'DB',
    title: 'DB Element',
    description: 'Convert DB printout PDF or BAX into structured Excel.',
    icon: Layers,
  },
  {
    type: 'PC',
    title: 'PC Element',
    description: 'Convert PC Element PDF or AAX into hardwired I/O Excel.',
    icon: Cpu,
  },
];

export function ElementTypeDialog({
  open,
  isStarting = false,
  onClose,
  onConfirm,
}: ElementTypeDialogProps) {
  const [selected, setSelected] = useState<ElementConversionType | null>(null);

  if (!open) return null;

  const handleClose = () => {
    if (isStarting) return;
    setSelected(null);
    onClose();
  };

  const handleConfirm = () => {
    if (!selected || isStarting) return;
    onConfirm(selected);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="element-type-dialog-title"
        className="bg-white border border-slate-200 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden text-slate-800"
      >
        <div className="px-6 py-4 border-b border-slate-200 flex items-start justify-between bg-slate-50/80 gap-3">
          <div>
            <h3
              id="element-type-dialog-title"
              className="text-sm font-semibold text-slate-900 tracking-tight"
            >
              Select conversion type
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Choose whether these files should run as DB Element or PC Element conversion.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={isStarting}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-100 transition disabled:opacity-50"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {OPTIONS.map(({ type, title, description, icon: Icon }) => {
            const isActive = selected === type;
            return (
              <button
                key={type}
                type="button"
                onClick={() => setSelected(type)}
                disabled={isStarting}
                className={`w-full flex items-start gap-3 rounded-lg border px-4 py-3.5 text-left transition ${
                  isActive
                    ? 'border-valmet-green bg-emerald-50/60 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                } disabled:opacity-60`}
              >
                <span
                  className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
                    isActive
                      ? 'bg-emerald-100 text-valmet-green'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </span>
                <span>
                  <span className="block text-sm font-bold text-slate-900">{title}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">{description}</span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="px-5 pb-5 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <button
            type="button"
            onClick={handleClose}
            disabled={isStarting}
            className="rounded-md border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!selected || isStarting}
            className="rounded-md bg-valmet-green px-4 py-2.5 text-sm font-bold text-white hover:bg-valmet-darkgreen transition disabled:opacity-50"
          >
            {isStarting ? 'Starting…' : 'Start conversion'}
          </button>
        </div>
      </div>
    </div>
  );
}
