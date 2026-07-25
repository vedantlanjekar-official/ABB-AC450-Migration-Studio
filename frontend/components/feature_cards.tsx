'use client';

import React from 'react';
import { FileText, Cpu, Database, Table, ShieldCheck, Zap } from 'lucide-react';

const features = [
  {
    icon: FileText,
    title: 'PDF Parsing Engine',
    desc: 'High-precision layout text extraction using pdfplumber with PyMuPDF rendering fallback.',
  },
  {
    icon: Database,
    title: 'DB Element Extraction',
    desc: 'Generic AC450 object boundary detection for AI, AO, PIDCON, MOTCON, VALVECON, DS, DAT & more.',
  },
  {
    icon: Cpu,
    title: 'Smart Parameter Detection',
    desc: 'Dynamic colon key-value pair parsing (:KEY VALUE) supporting unconstrained parameter structures.',
  },
  {
    icon: Table,
    title: 'Automatic Excel Generation',
    desc: 'Generates structured Valmet-compatible workbooks with dynamic sheets formatted per element type.',
  },
  {
    icon: ShieldCheck,
    title: 'Validation & Tolerant Engine',
    desc: 'Handles incomplete parameter sets without crashing. Generates comprehensive audit warning logs.',
  },
  {
    icon: Zap,
    title: 'High Speed Processing',
    desc: 'Asynchronous non-blocking background queue capable of parsing enterprise multi-page documents in seconds.',
  },
];

export function FeatureCards() {
  return (
    <div className="mt-12">
      <div className="text-center mb-8">
        <h3 className="text-lg font-bold text-slate-800 uppercase tracking-wider font-mono">
          Enterprise Industrial Features
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Engineered for DCS/PLC Automation Engineers & Systems Integrators
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-abb-red/50 hover:shadow-md transition group"
            >
              <div className="w-10 h-10 rounded-lg bg-slate-100 group-hover:bg-red-50 text-slate-700 group-hover:text-abb-red flex items-center justify-center mb-3 transition">
                <Icon className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-slate-900 group-hover:text-abb-red transition">
                {item.title}
              </h4>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                {item.desc}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
