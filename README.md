# ABB AC450 Engineering Data Converter (Phase 1: DB Element Converter)

Production-grade full-stack web application designed to convert **ABB Advant Controller 450 (AC450)** DB Element PDF printout files into **Valmet-compatible Excel workbooks (`.xlsx`)**.

---

## 🌟 Key Features

- **Generic & Extensible DB Element Parser**: Automatically detects all standard and custom AC450 element headers (`AI`, `AO`, `PIDCON`, `MOTCON`, `VALVECON`, `DS`, `DAT`, `TEXT`, `MANSTN`, `RATIOSTN`, `TTDVAR`) without hardcoded schemas.
- **Dynamic Parameter Extraction Engine**: Parses colon-prefixed key-value pairs (`:KEY VALUE`) into structured dictionaries.
- **Valmet-Compatible Multi-Sheet Excel Export**: Generates styled `.xlsx` workbooks with **one worksheet per element type** featuring industrial styling, zebra striping, auto column width, and dynamic headers.
- **Real-Time Progress & Stage Tracking**: 6-stage background processing engine reporting real-time progress percentages, timing, warnings, and error logs.
- **Interactive Data Grid Preview**: Live tabbed table preview on the frontend to inspect extracted parameters per sheet before downloading.
- **Industrial Enterprise UI**: Styled specifically for plant automation engineers (ABB Red `#D60000` accents, dark slate themes, crisp typography).

---

## 🏗️ Architecture & Technology Stack

### Frontend
- **Framework**: Next.js 15 (App Router, React 18/19)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v3 & Industrial Engineering Tokens
- **Icons**: Lucide React
- **State Management**: Zustand
- **API Polling & Querying**: TanStack React Query v5
- **Animations**: Framer Motion

### Backend
- **Framework**: FastAPI (Python 3.11+) & Uvicorn
- **PDF Extraction**: `pdfplumber` (Primary) + `PyMuPDF` / `fitz` (Fallback)
- **Excel Generation**: `openpyxl` & `XlsxWriter`
- **Validation**: Pydantic v2
- **Testing**: Pytest

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run backend test suite
python -m pytest tests

# Start FastAPI server (Port 8000)
python main.py
```
FastAPI interactive docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server (Port 3000)
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📂 Project Structure

```
ABB-AC450-CONVERTER/
├── frontend/                  # Next.js 15 App Router Frontend
│   ├── app/                   # App layout & pages
│   ├── components/            # UI Components (Dropzone, Results, Preview)
│   ├── hooks/                 # Custom React & React Query Hooks
│   ├── services/              # Axios API client
│   ├── store/                 # Zustand state store
│   └── types/                 # TypeScript interfaces
├── backend/                   # Python FastAPI Backend
│   ├── api/                   # REST API routes (Upload, Process, Status, Download)
│   ├── core/                  # Settings & logging
│   ├── parser/                # Text extraction & generic DB parser
│   ├── extractor/             # Parameter colon regex extractor
│   ├── mapper/                # Tabular element mapper & sheet grouping
│   ├── excel/                 # OpenPyXL Excel builder
│   └── tests/                 # Pytest test suite
├── examples/                  # Sample AC450 DB PDF & PDF generator
├── docs/                      # Architecture documentation
└── README.md
```

---

## 🧪 Running Sample Test Conversion

A sample generator script is included under `examples/generate_sample_pdf.py`.

```bash
# Generate sample AC450 DB PDF
python examples/generate_sample_pdf.py

# Run full integration test
python -m pytest backend/tests/test_api.py -v
```

---

## 🌐 Production Deployment Guide

- **Frontend (Vercel)**:
  Deploy the `frontend/` directory to Vercel. Set `NEXT_PUBLIC_API_URL` environment variable to point to your hosted FastAPI backend URL.
- **Backend (Render / Railway / AWS / Docker)**:
  Deploy the `backend/` directory using Uvicorn:
  `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4`
