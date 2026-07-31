from pathlib import Path
from typing import Callable, List, Optional
from dataclasses import dataclass
import gc
import os
from backend.core.logging import get_logger

@dataclass
class LineRecord:
    page_number: int
    line_number: int
    text: str

class PDFReader:
    """
    Stage 1 — PDF Extraction Module for DB Element listings.

    Prefer PyMuPDF on production hosts (Render free tier ~512 MB). pdfplumber
    with layout=True on multi-MB DB printouts routinely OOMs and restarts the
    worker, which the UI reports as a stale conversion failure.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def _prefer_pymupdf_first(self) -> bool:
        """Light-first mode is on by default; set DB_LIGHT_PDF_READ=0 to force pdfplumber."""
        return os.environ.get("DB_LIGHT_PDF_READ", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def extract_line_records(
        self,
        pdf_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[LineRecord]:
        """Extracts text lines page-by-page into a list of LineRecord instances."""
        if not pdf_path.exists():
            self.logger.error(f"PDF file not found at {pdf_path}")
            return []

        size_bytes = pdf_path.stat().st_size
        self.logger.info(
            f"PDFReader extracting {pdf_path.name} ({size_bytes} bytes); "
            f"light_first={self._prefer_pymupdf_first()}"
        )

        if self._prefer_pymupdf_first():
            records = self._extract_with_pymupdf(pdf_path, progress_callback)
            if records:
                return records
            self.logger.warning(
                f"PyMuPDF returned no text for {pdf_path.name}; trying pdfplumber fallback."
            )
            return self._extract_with_pdfplumber(pdf_path, progress_callback)

        records = self._extract_with_pdfplumber(pdf_path, progress_callback)
        if records:
            return records
        self.logger.warning(
            f"pdfplumber returned no text for {pdf_path.name}; trying PyMuPDF fallback."
        )
        return self._extract_with_pymupdf(pdf_path, progress_callback)

    def _extract_with_pymupdf(
        self,
        pdf_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[LineRecord]:
        import fitz

        line_records: List[LineRecord] = []
        self.logger.info(f"PDFReader opening {pdf_path.name} via PyMuPDF...")
        doc = fitz.open(pdf_path)
        try:
            total_pages = doc.page_count
            for page_idx in range(total_pages):
                page = doc.load_page(page_idx)
                # "text" is far cheaper than rawdict/blocks and enough for DB listings.
                text = page.get_text("text") or ""
                for line_idx, line in enumerate(text.splitlines(), start=1):
                    stripped = line.strip()
                    if stripped:
                        line_records.append(
                            LineRecord(
                                page_number=page_idx + 1,
                                line_number=line_idx,
                                text=stripped,
                            )
                        )
                if progress_callback and ((page_idx + 1) % 5 == 0 or page_idx + 1 == total_pages):
                    progress_callback(page_idx + 1, total_pages)
                # Free page resources promptly on low-RAM hosts.
                if (page_idx + 1) % 25 == 0:
                    gc.collect()
        finally:
            doc.close()

        self.logger.info(
            f"PDFReader extracted {len(line_records)} line(s) via PyMuPDF "
            f"from {pdf_path.name}."
        )
        return line_records

    def _extract_with_pdfplumber(
        self,
        pdf_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[LineRecord]:
        import pdfplumber

        line_records: List[LineRecord] = []
        self.logger.info(f"PDFReader opening {pdf_path.name} via pdfplumber...")
        # Avoid layout=True by default — it is much heavier and OOMs on Render free tier.
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    text = page.extract_text(layout=True) or ""
                for line_idx, line in enumerate(text.splitlines(), start=1):
                    stripped = line.strip()
                    if stripped:
                        line_records.append(
                            LineRecord(
                                page_number=page_idx,
                                line_number=line_idx,
                                text=stripped,
                            )
                        )
                if progress_callback and (page_idx % 5 == 0 or page_idx == total_pages):
                    progress_callback(page_idx, total_pages)
                if page_idx % 25 == 0:
                    gc.collect()

        self.logger.info(
            f"PDFReader extracted {len(line_records)} line(s) from {total_pages} "
            f"page(s) via pdfplumber."
        )
        return line_records
