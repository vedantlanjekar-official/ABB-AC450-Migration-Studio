'use client';

import React from 'react';
import { Download } from 'lucide-react';

const MANUAL_HREF = '/ABB-AC450-Migration-Studio-User-Manual.pdf';
const MANUAL_FILENAME = 'ABB-AC450-Migration-Studio-User-Manual.pdf';

const NAV_ITEMS = [
  { href: '#converter', label: 'Services' },
  { href: '#features', label: 'Features' },
  { href: '#workflow', label: 'Workflow' },
  { href: '#contact', label: 'Contact' },
];

export function Header() {
  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200 text-slate-900 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <a href="#hero" className="flex items-center space-x-3 sm:space-x-4 min-w-0">
          <img
            src="/valmet-logo.webp"
            alt="Valmet Logo"
            className="h-8 w-auto object-contain shrink-0"
          />
          <div className="flex items-center space-x-2.5 text-sm sm:text-base font-semibold text-slate-800 tracking-tight min-w-0">
            <span className="truncate">ABB AC450 Migration Studio</span>
            <span className="text-slate-300 font-light hidden sm:inline">|</span>
            <span className="text-slate-600 font-medium hidden lg:inline">Valmet Converter Suite</span>
          </div>
        </a>

        <div className="flex items-center gap-3 sm:gap-5 shrink-0">
          <nav className="hidden md:flex items-center gap-5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="hover:text-valmet-green transition-colors"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <a
            href={MANUAL_HREF}
            download={MANUAL_FILENAME}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-valmet-green hover:bg-valmet-darkgreen text-white text-[11px] font-bold uppercase tracking-wider transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">User Manual</span>
            <span className="sm:hidden">Manual</span>
          </a>
        </div>
      </div>
    </header>
  );
}
