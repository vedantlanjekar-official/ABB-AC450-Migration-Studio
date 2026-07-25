# ABB AC450 Engineering Converter Architecture Documentation

## System Overview

The **ABB AC450 Engineering Converter** is designed as a decoupled enterprise web application that parses ABB Advant Controller 450 (AC450) Database (DB) Element PDF printouts and transforms them into structured Valmet-compatible Excel workbooks (`.xlsx`).

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js 15 Frontend                  │
│       (App Router, React 18/19, Tailwind, Zustand)      │
└────────────────────────────┬────────────────────────────┘
                             │ REST API / Axios
┌────────────────────────────▼────────────────────────────┐
│                    Python FastAPI Backend               │
│                  (Uvicorn, Pydantic, Async)             │
└────────────────────────────┬────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     │                       │                       │
┌────▼─────────────────┐ ┌───▼──────────────────┐ ┌──▼──────────────────┐
│ PDF Text Extractor   │ │ Generic DB Parser    │ │ Dynamic Excel Gen   │
│ (pdfplumber/fitz)    │ │ (Regex & Tokenizer)  │ │ (OpenPyXL)          │
└──────────────────────┘ └──────────────────────┘ └─────────────────────┘
```

## Backend Pipeline Architecture

1. **PDF Text Extractor (`backend/parser/pdf_text_extractor.py`)**:
   - Primary engine: `pdfplumber` for structured layout & coordinate retention.
   - Fallback engine: `PyMuPDF` (`fitz`) for scanned or legacy PDF text stream rendering.

2. **Generic DB Element Parser (`backend/parser/db_element_parser.py`)**:
   - Header Regex Pattern: `^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\b`
   - Dynamically identifies element types (e.g., `AI`, `AO`, `PIDCON`, `MOTCON`, `VALVECON`, `DS`, `DAT`, `TEXT`, `MANSTN`, `RATIOSTN`, `TTDVAR`).
   - Isolates object boundaries without hardcoding schemas.

3. **Parameter Extractor (`backend/extractor/parameter_extractor.py`)**:
   - Parses colon-prefixed parameter key-value pairs (`:KEY VALUE`).
   - Handles quote-wrapped strings, unquoted numbers, booleans, and multiline values.

4. **Element Grouping Engine (`backend/mapper/element_mapper.py`)**:
   - Aggregates parsed objects by `element_type`.
   - Collects all unique parameter keys across all elements in a group to form full tabular column structures.

5. **Dynamic Excel Generator (`backend/excel/excel_generator.py`)**:
   - Builds openpyxl workbooks with **one sheet per element type**.
   - Applies industrial formatting: Navy/Slate headers (`#1E293B`), zebra striping, auto column width, gridlines.

## Extensibility & Future Phase Support

The application is structured to allow future extension without refactoring core components:
- **PC Element Module**: Can be plugged into `backend/parser/pc_element_parser.py` using the same service & mapper architecture.
- **Additional Exporters**: Exporters (CSV, XML, JSON) can implement a unified `BaseExporter` interface alongside `ExcelGenerator`.
- **Database / Cloud Storage**: Abstracted behind service interfaces for seamless integration with PostgreSQL, Cloud Storage, or S3.
