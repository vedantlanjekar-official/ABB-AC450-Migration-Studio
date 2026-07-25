from pathlib import Path
from typing import List
from dataclasses import dataclass
from backend.core.logging import get_logger

@dataclass
class PCLineRecord:
    page_number: int
    line_number: int
    text: str

class PCPDFReader:
    """
    PC Element PDF Line Reader Module.
    Extracts text line-by-line while preserving page and line indices.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def extract_line_records(self, pdf_path: Path) -> List[PCLineRecord]:
        """Extracts all non-empty line records from PDF file."""
        records: List[PCLineRecord] = []
        if not pdf_path.exists():
            self.logger.error(f"PCPDFReader error: PDF file not found at {pdf_path}")
            return records

        try:
            import pdfplumber
            self.logger.info(f"PCPDFReader reading PDF: {pdf_path.name} via pdfplumber...")
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(layout=True) or page.extract_text() or ""
                    for line_idx, line in enumerate(text.splitlines(), start=1):
                        stripped = line.strip()
                        if stripped:
                            records.append(PCLineRecord(page_number=page_idx, line_number=line_idx, text=stripped))
            
            self.logger.info(f"PCPDFReader extracted {len(records)} line(s) from {pdf_path.name}.")
            return records

        except Exception as e:
            self.logger.warning(f"PCPDFReader pdfplumber failed: {e}. Falling back to PyMuPDF...")
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                for page_idx in range(len(doc)):
                    page = doc.load_page(page_idx)
                    text = page.get_text() or ""
                    for line_idx, line in enumerate(text.splitlines(), start=1):
                        stripped = line.strip()
                        if stripped:
                            records.append(PCLineRecord(page_number=page_idx + 1, line_number=line_idx, text=stripped))
                doc.close()
                self.logger.info(f"PCPDFReader PyMuPDF fallback extracted {len(records)} line(s).")
                return records
            except Exception as ex:
                self.logger.error(f"PCPDFReader PyMuPDF fallback also failed: {ex}")
                return []
