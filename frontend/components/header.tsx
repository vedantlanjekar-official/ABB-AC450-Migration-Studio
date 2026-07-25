'use client';

import React from 'react';

export function Header() {

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200 text-slate-900 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left Side: Valmet Logo + Clean Simple Text Titles */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          {/* Official Valmet Logo WebP Image */}
          <img
            src="/valmet-logo.webp"
            alt="Valmet Logo"
            className="h-8 w-auto object-contain shrink-0"
          />

          {/* Simple Clean Title & Sub-title as in reference photo */}
          <div className="flex items-center space-x-2.5 text-sm sm:text-base font-semibold text-slate-800 tracking-tight">
            <span>ABB AC450 Migration Studio</span>
            <span className="text-slate-300 font-light">|</span>
            <span className="text-slate-600 font-medium hidden sm:inline">Valmet Converter Suite</span>
          </div>
        </div>

      </div>
    </header>
  );
}
