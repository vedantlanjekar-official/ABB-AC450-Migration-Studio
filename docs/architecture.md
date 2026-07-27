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

2. **DB Element I/O Parser (`backend/parser/db_element_parser.py`)**:
   - Header Regex Pattern: `^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\b`
   - Extracts only supported I/O families: `AI`, `AO`, `DI`, `DO`, `AI800`, `AO800`, `DI800`, `DO800`.
   - Unsupported object types (`AIC`, `AOC`, `DAT`, `PIDCON`, `MANSTN`, `TEXT`, etc.) are skipped during extraction.

3. **Parameter Extractor (`backend/extractor/parameter_extractor.py`)**:
   - Parses colon-prefixed parameter key-value pairs (`:KEY VALUE`).
   - Handles quote-wrapped strings, unquoted numbers, booleans, and multiline values.

4. **Element Grouping Engine (`backend/mapper/element_mapper.py`)**:
   - Aggregates parsed objects by `element_type`.
   - Collects all unique parameter keys across all elements in a group to form full tabular column structures.
   - Adds derived `Loop Tag` column (NAME with final suffix removed).

5. **Record Clubbing (`backend/mapper/record_clubber.py`)**:
   - Matches on common Loop Tag only (strip suffix: `940FQ390.MV` + `940FQ390.OUT` → `940FQ390`).
   - Within each club: `AI→AO`, `DO→DI`, `AI800→AO800`, `DO800→DI800`; valve `SV1→GSO→GSC`.
   - Unpaired records kept (no placeholders). Matching/clubbing is unchanged by presentation.

6. **Output Formatter (`backend/mapper/output_formatter.py`)**:
   - Post-clubbing presentation layer (row order only) immediately before Excel write.
   - Sequence: all `AI→AO` groups → `DO→DI` → `AI800→AO800` → `DO800→DI800`.
   - Preserves pair adjacency; renumbers `Index` to `1..N` for final sheet order.

7. **Dynamic Excel Generator (`backend/excel/excel_generator.py`)**:
   - Builds a single consolidated **Clubbed_IO** worksheet with consecutive paired rows.
   - Applies industrial formatting: Navy/Slate headers (`#1E293B`), zebra striping, auto column width, gridlines.

## Dual Conversion Modules

`ConversionService` routes by `conversion_type`:

| Type | Engine | Excel |
|------|--------|-------|
| **DB** | `backend/parser/*` + mapper | Multi-sheet Valmet workbook |
| **PC** | `backend/pc_element/parser/*` | Single-sheet `I_O_List` |

Full PC Element design, parsing rules, and verification results: [`docs/pc_element_module.md`](pc_element_module.md).

## Extensibility

- New ABB I/O prefixes: extend `grammar_parser.PREFIX_MAP` + detector regex + validator sets.
- Additional exporters (CSV, XML, JSON) can sit beside `ExcelGenerator`.
- Storage remains filesystem/temp — no database required.
