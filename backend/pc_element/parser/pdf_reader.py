"""
pdf_reader.py - Stage 1: Reading PDF documents with pdfplumber and PyMuPDF fallback.
Handles multi-page PDFs, character reconstruction for CAD/vector PDF files.
"""

from typing import List, Dict, Any, Optional
import os
import pdfplumber
import fitz  # PyMuPDF
from pydantic import BaseModel, Field


class PageContent(BaseModel):
    page_number: int
    text: str
    words: List[Dict[str, Any]] = Field(default_factory=list)
    raw_lines: List[str] = Field(default_factory=list)


class PDFReader:
    """Reads PDF pages using pdfplumber with PyMuPDF fallback and text reconstruction."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at path: {file_path}")

    def read_all_pages(self) -> List[PageContent]:
        """Reads every page in the PDF and returns structured PageContent objects."""
        pages: List[PageContent] = []
        try:
            pages = self._read_with_pdfplumber()
        except Exception as e:
            # Fallback to PyMuPDF if pdfplumber fails
            pages = self._read_with_pymupdf()

        # If pdfplumber returned empty text across pages, fallback to PyMuPDF
        if not pages or all(len(p.text.strip()) == 0 for p in pages):
            pages = self._read_with_pymupdf()

        return pages

    def _read_with_pdfplumber(self) -> List[PageContent]:
        pages_content: List[PageContent] = []
        with pdfplumber.open(self.file_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(layout=True) or page.extract_text() or ""
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=True
                ) or []
                
                # Reconstruct fragmented characters/words if needed
                reconstructed_lines = self._reconstruct_spatial_words(words)
                if reconstructed_lines and len("\n".join(reconstructed_lines)) > len(page_text):
                    combined_text = "\n".join(reconstructed_lines)
                    raw_lines = [line for line in reconstructed_lines if line.strip()]
                else:
                    combined_text = page_text
                    raw_lines = [line for line in page_text.splitlines() if line.strip()]

                pages_content.append(
                    PageContent(
                        page_number=idx,
                        text=combined_text,
                        words=words,
                        raw_lines=raw_lines if raw_lines else combined_text.splitlines()
                    )
                )
        return pages_content

    def _read_with_pymupdf(self) -> List[PageContent]:
        pages_content: List[PageContent] = []
        doc = fitz.open(self.file_path)
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            # Extract word blocks
            raw_words = page.get_text("words") or []
            words = [
                {
                    "text": w[4],
                    "x0": w[0],
                    "top": w[1],
                    "x1": w[2],
                    "bottom": w[3]
                }
                for w in raw_words
            ]
            raw_lines = [line for line in text.splitlines() if line.strip()]
            pages_content.append(
                PageContent(
                    page_number=idx,
                    text=text,
                    words=words,
                    raw_lines=raw_lines
                )
            )
        doc.close()
        return pages_content

    def _reconstruct_spatial_words(self, words: List[Dict[str, Any]]) -> List[str]:
        """Groups words/chars on the same horizontal line (y-level) into coherent lines."""
        if not words:
            return []

        # Sort words by top coordinate first
        sorted_by_top = sorted(words, key=lambda w: w.get("top", 0))

        lines: List[List[Dict[str, Any]]] = []
        y_tolerance = 3.5

        for w in sorted_by_top:
            w_top = w.get("top", 0)
            # Find if there is an existing line within y_tolerance
            matched_line = None
            for line in lines:
                if abs(line[0].get("top", 0) - w_top) <= y_tolerance:
                    matched_line = line
                    break
            if matched_line is not None:
                matched_line.append(w)
            else:
                lines.append([w])

        # Sort lines by their top coordinate (top-to-bottom)
        lines_sorted = sorted(lines, key=lambda line: line[0].get("top", 0))

        result_lines: List[str] = []
        for line_words in lines_sorted:
            # Sort words horizontally (left-to-right)
            line_words_sorted = sorted(line_words, key=lambda w: w.get("x0", 0))
            line_str = ""
            last_x1 = None
            for w in line_words_sorted:
                text_str = w.get("text", "")
                x0 = w.get("x0", 0)
                if last_x1 is not None and (x0 - last_x1) > 4.0:
                    line_str += " " + text_str
                else:
                    line_str += text_str
                last_x1 = w.get("x1", x0)
            result_lines.append(line_str)

        return result_lines
