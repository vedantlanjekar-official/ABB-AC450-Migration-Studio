from pathlib import Path
from typing import List, Dict, Any
import pdfplumber
import fitz  # PyMuPDF
from backend.core.logging import get_logger

class PDFTextExtractor:
    """
    Extracts text from PDF files using pdfplumber as primary engine
    and PyMuPDF (fitz) as fallback engine.
    """
    
    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def extract_text_pages(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts page-by-page text content from a PDF file.
        Returns a list of dicts: [{'page_number': int, 'text': str, 'engine': str}]
        """
        self.logger.info(f"Extracting text from PDF: {pdf_path.name} via pdfplumber")
        extracted_pages = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(layout=True) or page.extract_text() or ""
                    extracted_pages.append({
                        "page_number": idx,
                        "text": text,
                        "engine": "pdfplumber"
                    })
            
            # Verify if pdfplumber extracted meaningful content
            total_chars = sum(len(p["text"].strip()) for p in extracted_pages)
            if total_chars > 0:
                self.logger.info(f"Successfully extracted {len(extracted_pages)} pages ({total_chars} chars) using pdfplumber")
                return extracted_pages
            else:
                self.logger.warning("pdfplumber returned empty text. Triggering PyMuPDF fallback.")
        except Exception as e:
            self.logger.warning(f"pdfplumber extraction failed on {pdf_path.name}: {e}. Triggering PyMuPDF fallback.")
        
        # Fallback to PyMuPDF
        return self._extract_with_fitz(pdf_path)

    def _extract_with_fitz(self, pdf_path: Path) -> List[Dict[str, Any]]:
        self.logger.info(f"Extracting text from PDF: {pdf_path.name} via PyMuPDF (fitz)")
        extracted_pages = []
        try:
            doc = fitz.open(pdf_path)
            for idx, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                extracted_pages.append({
                    "page_number": idx,
                    "text": text,
                    "engine": "pymupdf"
                })
            doc.close()
            total_chars = sum(len(p["text"].strip()) for p in extracted_pages)
            self.logger.info(f"PyMuPDF fallback extracted {len(extracted_pages)} pages ({total_chars} chars)")
        except Exception as e:
            self.logger.error(f"PyMuPDF fallback also failed on {pdf_path.name}: {e}")
            
        return extracted_pages
