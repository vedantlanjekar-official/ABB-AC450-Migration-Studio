import React from 'react';
import { Metadata } from 'next';
import { Header } from '../components/header';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'ABB AC450 Migration Studio',
  description: 'Convert ABB Advant Controller 450 DB Element PDFs into Valmet-compatible Excel formats with automated parsing, validation, and structured export.',
  icons: {
    icon: '/valmet-logo-bg.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col antialiased" suppressHydrationWarning>
        <Providers>
          <Header />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
          <footer className="bg-white border-t border-slate-200 py-8 text-center text-xs text-slate-500">
            <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-800 font-sans">ABB AC450 Migration Studio</span>
                <span className="text-slate-300">|</span>
                <span className="text-valmet-green font-semibold">Valmet Integration Suite</span>
              </div>
              <div className="text-slate-500">
                © 2026 ABB AC450 Migration Studio. Engineering Data Migration Platform. All Rights Reserved.
              </div>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
