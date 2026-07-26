"""
pdf_reader.py - Stage 1: Multi-layer PDF text extraction for ABB PC Diagrams.

Merges pdfplumber layout text, spatial word reconstruction, and PyMuPDF layers so
CAD/vector drawings yield the maximum recoverable engineering text without OCR when
selectable text exists. Falls back to optional OCR only when text density is too low.
"""

from typing import List, Dict, Any, Optional, Set
import os
import logging
import pdfplumber
import fitz  # PyMuPDF
from pydantic import BaseModel, Field

logger = logging.getLogger("pc_element_parser")


class PageContent(BaseModel):
    page_number: int
    text: str
    words: List[Dict[str, Any]] = Field(default_factory=list)
    raw_lines: List[str] = Field(default_factory=list)
    text_layers: Dict[str, str] = Field(default_factory=dict)
    low_text_density: bool = False


class PDFReader:
    """Multi-layer PDF reader optimized for ABB AC450 PC DIAGRAM drawings."""

    MIN_CHARS_PER_PAGE = 80

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at path: {file_path}")

    def read_all_pages(self) -> List[PageContent]:
        """Fuse pdfplumber + PyMuPDF layers per page for maximum recall."""
        plumber_pages: List[PageContent] = []
        try:
            plumber_pages = self._read_with_pdfplumber()
        except Exception as exc:
            logger.warning(f"pdfplumber failed ({exc}); using PyMuPDF only")

        fitz_pages = self._read_with_pymupdf()

        if not plumber_pages:
            return self._maybe_ocr(fitz_pages)

        merged: List[PageContent] = []
        for idx in range(max(len(plumber_pages), len(fitz_pages))):
            p = plumber_pages[idx] if idx < len(plumber_pages) else None
            f = fitz_pages[idx] if idx < len(fitz_pages) else None
            merged.append(self._merge_page_layers(p, f, idx + 1))

        return self._maybe_ocr(merged)

    def _merge_page_layers(
        self,
        plumber: Optional[PageContent],
        fitz_page: Optional[PageContent],
        page_number: int,
    ) -> PageContent:
        layers: Dict[str, str] = {}
        words: List[Dict[str, Any]] = []
        lines: Set[str] = set()

        if plumber:
            layers["plumber"] = plumber.text or ""
            layers["plumber_lines"] = "\n".join(plumber.raw_lines)
            words = list(plumber.words or [])
            for ln in plumber.raw_lines:
                if ln.strip():
                    lines.add(ln.strip())

        if fitz_page:
            layers["fitz"] = fitz_page.text or ""
            layers["fitz_lines"] = "\n".join(fitz_page.raw_lines)
            if not words and fitz_page.words:
                words = list(fitz_page.words)
            elif fitz_page.words and len(fitz_page.words) > len(words):
                # Prefer denser word stream for spatial assembly
                words = list(fitz_page.words)
            for ln in fitz_page.raw_lines:
                if ln.strip():
                    lines.add(ln.strip())

        # Spatial reconstruction from the richest word stream
        spatial_lines = self._reconstruct_spatial_words(words)
        if spatial_lines:
            layers["spatial"] = "\n".join(spatial_lines)
            for ln in spatial_lines:
                if ln.strip():
                    lines.add(ln.strip())

        # Spaced word join helps when CAD splits characters oddly
        if words:
            layers["words_joined"] = " ".join(w.get("text", "") for w in words)

        # Choose primary text = longest non-empty layer
        primary = max(layers.values(), key=lambda t: len(t or ""), default="")
        raw_lines = sorted(lines, key=lambda s: (len(s), s))
        # Prefer spatial/plumber line order when available
        if spatial_lines:
            raw_lines = [ln for ln in spatial_lines if ln.strip()]
        elif plumber and plumber.raw_lines:
            raw_lines = [ln for ln in plumber.raw_lines if ln.strip()]
        elif fitz_page and fitz_page.raw_lines:
            raw_lines = [ln for ln in fitz_page.raw_lines if ln.strip()]

        low_density = len((primary or "").strip()) < self.MIN_CHARS_PER_PAGE

        return PageContent(
            page_number=page_number,
            text=primary or "",
            words=words,
            raw_lines=raw_lines,
            text_layers=layers,
            low_text_density=low_density,
        )

    def _maybe_ocr(self, pages: List[PageContent]) -> List[PageContent]:
        """Optional OCR fallback when most pages have almost no selectable text."""
        if not pages:
            return pages
        low = sum(1 for p in pages if p.low_text_density)
        if low < max(1, len(pages) // 2):
            return pages

        try:
            ocr_pages = self._ocr_with_pymupdf_textpage(pages)
            if ocr_pages:
                logger.info(f"OCR/text-page enrichment applied to {low} low-density pages")
                return ocr_pages
        except Exception as exc:
            logger.warning(f"OCR fallback unavailable: {exc}")
        return pages

    def _ocr_with_pymupdf_textpage(self, pages: List[PageContent]) -> List[PageContent]:
        """
        Attempt denser text extraction via PyMuPDF TextPage.
        Full Tesseract OCR is used only if pytesseract + render are available.
        """
        doc = fitz.open(self.file_path)
        enriched: List[PageContent] = []
        for idx, page in enumerate(pages):
            if not page.low_text_density:
                enriched.append(page)
                continue

            mp = doc[idx]
            text = mp.get_text("text") or page.text
            # Try rendering + tesseract if installed
            try:
                import pytesseract  # type: ignore
                from PIL import Image
                import io

                pix = mp.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img) or ""
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    page.text_layers["ocr"] = ocr_text
            except Exception:
                pass

            lines = [ln for ln in text.splitlines() if ln.strip()]
            enriched.append(
                PageContent(
                    page_number=page.page_number,
                    text=text,
                    words=page.words,
                    raw_lines=lines or page.raw_lines,
                    text_layers=page.text_layers,
                    low_text_density=len(text.strip()) < self.MIN_CHARS_PER_PAGE,
                )
            )
        doc.close()
        return enriched

    def _read_with_pdfplumber(self) -> List[PageContent]:
        pages_content: List[PageContent] = []
        with pdfplumber.open(self.file_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(layout=True) or page.extract_text() or ""
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=True,
                ) or []

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
                        raw_lines=raw_lines if raw_lines else combined_text.splitlines(),
                        text_layers={"plumber": combined_text},
                    )
                )
        return pages_content

    def _read_with_pymupdf(self) -> List[PageContent]:
        pages_content: List[PageContent] = []
        doc = fitz.open(self.file_path)
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            raw_words = page.get_text("words") or []
            words = [
                {
                    "text": w[4],
                    "x0": w[0],
                    "top": w[1],
                    "x1": w[2],
                    "bottom": w[3],
                }
                for w in raw_words
            ]
            raw_lines = [line for line in text.splitlines() if line.strip()]
            pages_content.append(
                PageContent(
                    page_number=idx,
                    text=text,
                    words=words,
                    raw_lines=raw_lines,
                    text_layers={"fitz": text},
                )
            )
        doc.close()
        return pages_content

    def _reconstruct_spatial_words(self, words: List[Dict[str, Any]]) -> List[str]:
        """Groups words on the same horizontal band into coherent text lines."""
        if not words:
            return []

        sorted_by_top = sorted(words, key=lambda w: w.get("top", 0))
        lines: List[List[Dict[str, Any]]] = []
        y_tolerance = 3.5

        for w in sorted_by_top:
            w_top = w.get("top", 0)
            matched_line = None
            for line in lines:
                if abs(line[0].get("top", 0) - w_top) <= y_tolerance:
                    matched_line = line
                    break
            if matched_line is not None:
                matched_line.append(w)
            else:
                lines.append([w])

        lines_sorted = sorted(lines, key=lambda line: line[0].get("top", 0))
        result_lines: List[str] = []
        for line_words in lines_sorted:
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
