from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from backend.core.logging import get_logger

@dataclass
class LineRecord:
    page_number: int
    line_number: int
    text: str

class PDFReader:
    """
    Stage 1 — PDF Extraction Module.
    Reads every page of an ABB Database Listing PDF preserving reading order and line sequence.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def extract_line_records(self, pdf_path: Path) -> List[LineRecord]:
        """Extracts text lines page-by-page into a list of LineRecord instances."""
        line_records: List[LineRecord] = []

        if not pdf_path.exists():
            self.logger.error(f"PDF file not found at {pdf_path}")
            return line_records

        try:
            import pdfplumber
            self.logger.info(f"PDFReader opening {pdf_path.name} via pdfplumber...")
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(layout=True) or page.extract_text() or ""
                    lines = text.splitlines()
                    for line_idx, line in enumerate(lines, start=1):
                        if line.strip():
                            line_records.append(
                                LineRecord(page_number=page_idx, line_number=line_idx, text=line.strip())
                            )
            self.logger.info(f"PDFReader extracted {len(line_records)} line(s) from {len(pdf.pages)} page(s) via pdfplumber.")
            return line_records
        except Exception as e:
            self.logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}. Falling back to PyMuPDF...")

        try:
            import fitz
            doc = fitz.open(pdf_path)
            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                lines = text.splitlines()
                for line_idx, line in enumerate(lines, start=1):
                    if line.strip():
                        line_records.append(
                            LineRecord(page_number=page_idx, line_number=line_idx, text=line.strip())
                        )
            doc.close()
            self.logger.info(f"PDFReader extracted {len(line_records)} line(s) via PyMuPDF.")
            return line_records
        except Exception as ex:
            self.logger.error(f"PyMuPDF fallback failed: {ex}")
            raise ex
