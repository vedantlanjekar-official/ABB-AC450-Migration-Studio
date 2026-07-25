'use client';

import React from 'react';
import { 
  ArrowRight, 
  FileText, 
  Cpu, 
  Database, 
  Table, 
  ShieldCheck, 
  Zap, 
  Mail, 
  Globe, 
  Shield,
  Layers,
  Sliders,
  FileSpreadsheet
} from 'lucide-react';
import { useConverterStore } from '../store/converter_store';
import { Dropzone } from './dropzone';
import { ProcessingView } from './processing_view';
import { ResultsView } from './results_view';

export function FramerLanding() {
  const { stage } = useConverterStore();

  return (
    <div className="space-y-20 pb-16">
      {/* ============================================================ */}
      {/* 1. HERO SECTION                                              */}
      {/* ============================================================ */}
      <section id="hero" className="relative pt-4 pb-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          {/* Left Column */}
          <div className="lg:col-span-6 space-y-6">
            {/* Tagline Pill: LEAD THE WAY as in screenshot */}
            <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-valmet-lightgreen text-valmet-green border border-valmet-green/30 text-xs font-bold tracking-wider uppercase">
              <Shield className="w-3.5 h-3.5" />
              <span>LEAD THE WAY</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-[1.1]">
              ABB AC450 <span className="text-valmet-green">Migration Studio</span>
            </h1>

            <p className="text-base sm:text-lg font-semibold text-slate-800 leading-snug">
              Transforming Engineering Data, Project Execution, and Site Operations Through a Unified Digital Platform.
            </p>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              ABB AC450 Migration Studio empowers engineering teams, project managers, and stakeholders with a centralized platform for automated parsing, validation, safety compliance, and real-time operational conversion across every stage of DCS/PLC migration.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <a
                href="#converter"
                className="px-6 py-3 bg-valmet-green hover:bg-valmet-darkgreen text-white font-bold text-sm rounded-lg transition shadow-sm flex items-center space-x-2"
              >
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4" />
              </a>
              <a
                href="#features"
                className="px-6 py-3 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-lg border border-slate-300 transition"
              >
                Explore Features
              </a>
            </div>
          </div>

          {/* Right Column: Provided Hero Page Image */}
          <div className="lg:col-span-6 relative">
            <div className="bg-white rounded-2xl p-2 shadow-lg border border-slate-200 overflow-hidden">
              <img
                src="/HeroPage.png"
                alt="Valmet Site Netra Ecosystem / ABB AC450 Migration Studio"
                className="w-full h-auto object-cover rounded-xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* 2. MAIN CONVERTER SECTION                                    */}
      {/* ============================================================ */}
      <section id="converter" className="scroll-mt-24">
        <div className="text-center max-w-3xl mx-auto mb-10">
          <span className="text-valmet-green text-xs sm:text-sm font-bold uppercase tracking-widest font-sans block mb-1">
            CONVERSION ENGINE
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight uppercase font-sans">
            ENGINEERING FILE CONVERTER
          </h2>
          <div className="w-12 h-1 bg-valmet-green mx-auto my-3 rounded-full" />
          <p className="text-slate-600 text-xs sm:text-sm font-normal">
            Upload ABB AC450 engineering documents and automatically generate Valmet-compatible engineering outputs.
          </p>
        </div>

        {/* Interactive Converter View Router */}
        {stage === 'upload' && <Dropzone />}

        {stage === 'processing' && <ProcessingView />}

        {stage === 'results' && <ResultsView />}
      </section>

      {/* ============================================================ */}
      {/* 3. KEY FEATURES SECTION                                      */}
      {/* ============================================================ */}
      <section id="features" className="scroll-mt-24 border-t border-slate-200 pt-16">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <span className="text-valmet-green text-xs sm:text-sm font-bold uppercase tracking-widest font-sans block mb-1">
            CAPABILITIES
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight uppercase font-sans">
            KEY FEATURES
          </h2>
          <div className="w-12 h-1 bg-valmet-green mx-auto my-3 rounded-full" />
          <p className="text-slate-600 text-xs sm:text-sm font-normal">
            Click on any feature card to view its comprehensive capabilities and detailed specifications.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureItem
            icon={FileText}
            title="Intelligent PDF Parsing"
            description="Automatically understands complex ABB AC450 engineering document structures with multi-column AST detection."
          />
          <FeatureItem
            icon={Database}
            title="Database Element Conversion"
            description="Converts AI, AO, DI, DO, PIDCON, MOTCON and all engineering database objects accurately into structured schemas."
          />
          <FeatureItem
            icon={Cpu}
            title="PC Element Processing"
            description="Automatically extracts engineering references, loop tags, device tags and hardware channel IO mappings."
          />
          <FeatureItem
            icon={ShieldCheck}
            title="Engineering Validation"
            description="Performs automatic validation checks to ensure complete, consistent, and error-free engineering outputs."
          />
          <FeatureItem
            icon={Table}
            title="Excel Generation"
            description="Creates standardized Valmet-compatible Excel deliverables organized by sheet, ready for direct project import."
          />
          <FeatureItem
            icon={Zap}
            title="High Performance"
            description="Processes large enterprise engineering projects containing thousands of control elements in seconds."
          />
        </div>
      </section>

      {/* ============================================================ */}
      {/* 4. PLATFORM WORKFLOW (10 DATA PROCESSING STAGES)            */}
      {/* ============================================================ */}
      <section id="workflow" className="scroll-mt-24 border-t border-slate-200 pt-16">
        <div className="text-center max-w-3xl mx-auto mb-10">
          <span className="text-valmet-green text-xs sm:text-sm font-bold uppercase tracking-widest font-sans block mb-1">
            STEP-BY-STEP AUTOMATION PIPELINE
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight uppercase font-sans">
            PLATFORM WORKFLOW
          </h2>
          <div className="w-12 h-1 bg-valmet-green mx-auto my-3 rounded-full" />
          <p className="text-slate-600 text-xs sm:text-sm font-normal">
            End-to-end 10-stage automated compiler pipeline converting raw ABB AC450 PDF printouts into Valmet deliverables.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-5">
          {[
            { icon: FileText, title: 'PDF Extraction', desc: 'Page Layout & Vector Text Extraction' },
            { icon: ShieldCheck, title: 'Noise Removal', desc: 'Filtering Header/Footer Repetitive Lines' },
            { icon: Layers, title: 'Page Merging', desc: 'Multi-Page Document Stitching & Alignment' },
            { icon: Cpu, title: 'Tokenization', desc: 'Lexical Tokenization & Line Break Analysis' },
            { icon: Database, title: 'Default Construction', desc: 'Default Section Library Building' },
            { icon: Table, title: 'Inheritance Profiling', desc: 'Multi-Block Profile & Hierarchy Extraction' },
            { icon: Zap, title: 'Object Extraction', desc: 'Tag Boundary & Key-Value Parameter Parsing' },
            { icon: Sliders, title: 'Default Merging', desc: 'Family Default Inheritance & Overrides' },
            { icon: Shield, title: 'Data Validation', desc: 'Engineering Integrity & Range Validation' },
            { icon: FileSpreadsheet, title: 'Excel Generation', desc: 'Multi-Sheet Valmet Excel (.xlsx) Structuring' },
          ].map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={idx}
                className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between text-center shadow-xs hover:border-valmet-green hover:shadow-md transition-all group"
              >
                <div className="w-11 h-11 rounded-xl bg-valmet-lightgreen text-valmet-green flex items-center justify-center mx-auto mb-4 border border-valmet-green/20 group-hover:bg-valmet-green group-hover:text-white group-hover:scale-105 transition-all">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-valmet-green transition-colors">{step.title}</h4>
                  <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ============================================================ */}
      {/* 5. CONTACT SECTION                                           */}
      {/* ============================================================ */}
      <section id="contact" className="scroll-mt-24 border-t border-slate-200 pt-16">
        <div className="max-w-4xl mx-auto text-center mb-12">
          <span className="text-valmet-green text-xs sm:text-sm font-bold uppercase tracking-widest font-sans block mb-1">
            COMMUNICATION
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight uppercase font-sans">
            GET IN TOUCH
          </h2>
          <div className="w-12 h-1 bg-valmet-green mx-auto my-3 rounded-full" />
          <p className="text-slate-600 text-xs sm:text-sm font-normal leading-relaxed">
            Whether you're migrating a single control system or managing a large industrial modernization project, ABB AC450 Migration Studio helps engineering teams streamline the entire migration process with accuracy, speed, and confidence.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Card 1: Enquiries */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-mono text-valmet-green">
              Business Enquiries
            </h3>

            <div className="space-y-3 text-xs text-slate-700">
              <div className="flex items-center space-x-3">
                <Mail className="w-4 h-4 text-valmet-green shrink-0" />
                <div>
                  <span className="font-semibold text-slate-500 block">Email</span>
                  <a href="mailto:vedantlanjekar456@gmail.com" className="text-slate-900 hover:text-valmet-green font-medium">
                    vedantlanjekar456@gmail.com
                  </a>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <Globe className="w-4 h-4 text-valmet-green shrink-0" />
                <div>
                  <span className="font-semibold text-slate-500 block">Website</span>
                  <a href="http://www.valmet.com" target="_blank" rel="noreferrer" className="text-slate-900 hover:text-valmet-green font-medium">
                    www.valmet.com
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Development Team */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-mono text-valmet-green">
              Development Team
            </h3>

            <div className="space-y-1 text-xs text-slate-700">
              <div className="font-bold text-slate-900 text-sm">ABB AC450 Migration Studio</div>
              <div className="text-slate-500 font-medium">Engineering Automation Platform</div>
              <p className="text-slate-600 mt-2 leading-relaxed">
                Designed for industrial control system migration, engineering data conversion, and Valmet integration.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

// Subcomponent
function FeatureItem({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:border-valmet-green/40 hover:shadow-md transition-all group">
      <div className="w-10 h-10 rounded-xl bg-valmet-lightgreen text-valmet-green flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
        <Icon className="w-5 h-5" />
      </div>
      <h3 className="text-base font-bold text-slate-900">{title}</h3>
      <p className="text-xs text-slate-600 mt-2 leading-relaxed">{description}</p>
    </div>
  );
}
