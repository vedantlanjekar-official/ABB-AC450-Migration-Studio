from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from backend.core.logging import get_logger

@dataclass
class PageObject:
    page_number: int
    raw_text: str

class PDFLoader:
    """
    Stage 1 — PDF Extraction Module.
    Reads every page and extracts text exactly preserving reading order.
    Uses pdfplumber with PyMuPDF fallback.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def load_pdf_pages(self, pdf_path: Path) -> List[PageObject]:
        """
        Loads PDF text page-by-page into a list of PageObjects.
        """
        pages: List[PageObject] = []
        if not pdf_path.exists():
            self.logger.error(f"PDF file not found at {pdf_path}")
            return pages

        # Primary extraction using pdfplumber
        try:
            import pdfplumber
            self.logger.info(f"PDFLoader reading {pdf_path.name} via pdfplumber...")
            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    txt = page.extract_text(layout=True) or page.extract_text() or ""
                    pages.append(PageObject(page_number=idx, raw_text=txt))
            self.logger.info(f"PDFLoader extracted {len(pages)} pages via pdfplumber.")
            return pages
        except Exception as e:
            self.logger.warning(f"pdfplumber extraction failed for {pdf_path.name}: {e}. Falling back to PyMuPDF...")

        # Fallback extraction using PyMuPDF (fitz)
        try:
            import fitz
            doc = fitz.open(pdf_path)
            for idx, page in enumerate(doc, start=1):
                txt = page.get_text("text") or ""
                pages.append(PageObject(page_number=idx, raw_text=txt))
            doc.close()
            self.logger.info(f"PDFLoader extracted {len(pages)} pages via PyMuPDF.")
            return pages
        except Exception as ex:
            self.logger.error(f"PyMuPDF fallback extraction failed: {ex}")
            raise ex
