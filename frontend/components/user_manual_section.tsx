'use client';

import React from 'react';
import {
  BookOpen,
  Download,
  ExternalLink,
  FileText,
  Shield,
} from 'lucide-react';

const MANUAL_HREF = '/ABB-AC450-Migration-Studio-User-Manual.pdf';
const MANUAL_FILENAME = 'ABB-AC450-Migration-Studio-User-Manual.pdf';

const DOCUMENT_CONTROL = [
  { label: 'Document title', value: 'ABB AC450 Migration Studio — Enterprise User Manual' },
  { label: 'Document type', value: 'Controlled operating manual' },
  { label: 'Version', value: '1.0.0' },
  { label: 'Status', value: 'Production release reference' },
  { label: 'Issue date', value: '15 August 2026' },
  { label: 'Pages', value: '131' },
  { label: 'File size', value: '2.0 MB (PDF)' },
  { label: 'Prepared for', value: 'Valmet engineering projects' },
  { label: 'Owner', value: 'Engineering tools / project delivery' },
  { label: 'Classification', value: 'Project-controlled — retain with source records' },
];

const CHAPTERS = [
  { no: '01', title: 'Introduction and Scope' },
  { no: '02', title: 'Product Overview and Architecture' },
  { no: '03', title: 'Access, Installation, and Configuration' },
  { no: '04', title: 'User Interface and Navigation' },
  { no: '05', title: 'End-to-End Engineering Workflow' },
  { no: '06', title: 'DB Element Converter' },
  { no: '07', title: 'PC Element Converter' },
  { no: '08', title: 'Engineering Tag Comparator' },
  { no: '09', title: 'I/O Address Generator' },
  { no: '10', title: 'ABB Engineering Template Generator' },
  { no: '11', title: 'Output Workbook Reference' },
  { no: '12', title: 'Validation, Review, and Quality Assurance' },
  { no: '13', title: 'Troubleshooting and Error Handling' },
  { no: '14', title: 'Frequently Asked Questions' },
  { no: '15', title: 'Security, Performance, and Maintenance' },
  { no: '16', title: 'Developer and Deployment Handover' },
  { no: '17', title: 'Appendices and Glossary' },
];

const READING_GUIDE = [
  {
    range: 'Chapters 1–5',
    title: 'Foundation',
    detail: 'Read before operating any module. Covers scope, architecture, access, interface, and the end-to-end sequence.',
  },
  {
    range: 'Chapters 6–10',
    title: 'Module procedures',
    detail: 'Step-by-step operation of the five conversion services, including required inputs and expected Excel outputs.',
  },
  {
    range: 'Chapters 11–17',
    title: 'Assurance and handover',
    detail: 'Workbook contracts, review practice, troubleshooting, FAQ, security, deployment, and glossary.',
  },
];

export function UserManualSection() {
  return (
    <section id="user-manual" className="scroll-mt-24 border-t border-slate-200 pt-16">
      <div className="text-center max-w-3xl mx-auto mb-12">
        <span className="text-valmet-green text-xs sm:text-sm font-bold uppercase tracking-widest font-sans block mb-1">
          Controlled Documentation
        </span>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight uppercase font-sans">
          User Manual
        </h2>
        <div className="w-12 h-1 bg-valmet-green mx-auto my-3 rounded-full" />
        <p className="text-slate-600 text-xs sm:text-sm font-normal leading-relaxed">
          Official enterprise operating manual for ABB AC450 Migration Studio. Download the controlled PDF
          for commissioning, instrumentation, process, and project engineering teams.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-10">
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-valmet-green" />
              <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-valmet-green">
                Document Control
              </h3>
            </div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 font-mono">
              UM-AC450-1.0.0
            </span>
          </div>
          <dl className="divide-y divide-slate-100">
            {DOCUMENT_CONTROL.map((row) => (
              <div
                key={row.label}
                className="grid grid-cols-1 sm:grid-cols-12 gap-1 sm:gap-4 px-6 py-3"
              >
                <dt className="sm:col-span-4 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  {row.label}
                </dt>
                <dd className="sm:col-span-8 text-sm text-slate-900 font-medium leading-snug">
                  {row.value}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="lg:col-span-5 space-y-5">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-14 h-14 rounded-xl bg-valmet-lightgreen text-valmet-green border border-valmet-green/20 flex items-center justify-center shrink-0">
                <FileText className="w-7 h-7" />
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-widest text-valmet-green mb-1">
                  Official PDF
                </p>
                <h3 className="text-lg font-bold text-slate-900 leading-snug">
                  Enterprise User Manual
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Portable Document Format · Version 1.0.0 · 131 pages
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed mb-6">
              This controlled manual describes intended operation of the platform. Local project
              procedures, approved templates, and customer requirements remain authoritative where
              they differ from this guide. Engineering accountability is not transferred by conversion.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <a
                href={MANUAL_HREF}
                download={MANUAL_FILENAME}
                className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 bg-valmet-green hover:bg-valmet-darkgreen text-white font-bold text-sm rounded-lg transition shadow-sm"
              >
                <Download className="w-4 h-4" />
                <span>Download PDF</span>
              </a>
              <a
                href={MANUAL_HREF}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-lg border border-slate-300 transition"
              >
                <ExternalLink className="w-4 h-4" />
                <span>Open in Browser</span>
              </a>
            </div>
          </div>

          <div className="rounded-2xl border border-valmet-green/25 bg-valmet-lightgreen/60 p-5">
            <p className="text-[11px] font-bold uppercase tracking-widest text-valmet-green mb-3">
              How to use this manual
            </p>
            <ul className="space-y-3">
              {READING_GUIDE.map((item) => (
                <li key={item.range} className="text-xs text-slate-700 leading-relaxed">
                  <span className="font-bold text-slate-900">{item.range} — {item.title}. </span>
                  {item.detail}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-slate-200 bg-slate-50/80">
          <BookOpen className="w-4 h-4 text-valmet-green" />
          <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-valmet-green">
            Table of Contents
          </h3>
        </div>
        <ol className="grid grid-cols-1 md:grid-cols-2">
          {CHAPTERS.map((chapter) => (
            <li
              key={chapter.no}
              className="flex items-baseline gap-4 px-6 py-3 border-b border-slate-100"
            >
              <span className="font-mono text-[11px] font-bold text-valmet-green shrink-0 w-6">
                {chapter.no}
              </span>
              <span className="text-sm font-medium text-slate-800">{chapter.title}</span>
            </li>
          ))}
        </ol>
      </div>

      <p className="mt-6 text-[11px] text-slate-500 leading-relaxed max-w-4xl mx-auto text-center">
        Confidentiality: this manual may contain process terminology and engineering conventions that are
        meaningful only in a controlled project context. Do not place customer engineering files, production
        credentials, or personal data in shared locations merely to perform a conversion. Retain source
        records and generated workbooks in accordance with the project document-control plan.
      </p>
    </section>
  );
}
