'use client';

import React, { useState } from 'react';
import { Table, Search, Tag, Eye } from 'lucide-react';

interface DataGridPreviewProps {
  previewData: Record<string, Record<string, any>[]>;
}

export function DataGridPreview({ previewData }: DataGridPreviewProps) {
  const sheetNames = Object.keys(previewData);
  const [activeTab, setActiveTab] = useState<string>(sheetNames[0] || '');
  const [searchTerm, setSearchTerm] = useState<string>('');

  if (sheetNames.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-xs text-slate-400">
        No element preview data available.
      </div>
    );
  }

  const currentRows = previewData[activeTab] || [];
  const columns = currentRows.length > 0 ? Object.keys(currentRows[0]) : [];

  const filteredRows = currentRows.filter((row) =>
    Object.values(row).some((val) =>
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 font-mono flex items-center space-x-2">
            <Eye className="w-4 h-4 text-abb-red" />
            <span>Extracted DB Element Data Preview</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Interactive preview of parsed parameters (showing top records per element worksheet)
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search parameters or tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:border-abb-red"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 overflow-x-auto pb-2 mb-4">
        {sheetNames.map((sheet) => {
          const count = previewData[sheet]?.length || 0;
          const isActive = activeTab === sheet;
          return (
            <button
              key={sheet}
              onClick={() => setActiveTab(sheet)}
              className={`px-3 py-1.5 text-xs font-bold font-mono rounded-lg transition shrink-0 flex items-center space-x-1.5 ${
                isActive
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <span>{sheet}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  isActive ? 'bg-abb-red text-white' : 'bg-slate-200 text-slate-600'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Data Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200 max-h-96">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900 text-slate-200 font-mono text-[11px]">
            <tr>
              {columns.map((col) => (
                <th key={col} className="px-3 py-2.5 font-bold tracking-wider border-r border-slate-800 last:border-0">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 font-sans">
            {filteredRows.length > 0 ? (
              filteredRows.map((row, idx) => (
                <tr
                  key={idx}
                  className={idx % 2 === 0 ? 'bg-white hover:bg-slate-50' : 'bg-slate-50/50 hover:bg-slate-100/50'}
                >
                  {columns.map((col) => (
                    <td
                      key={col}
                      className={`px-3 py-2 border-r border-slate-100 last:border-0 ${
                        col === 'Tag' || col === 'NAME' ? 'font-mono font-bold text-slate-900' : 'text-slate-700'
                      }`}
                    >
                      {String(row[col] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length || 1} className="p-6 text-center text-slate-400">
                  No matching records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
