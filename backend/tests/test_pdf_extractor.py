import pytest
from pathlib import Path
from backend.parser.pdf_text_extractor import PDFTextExtractor

def test_pdf_text_extraction():
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_ac450_db.pdf"
    assert sample_pdf.exists(), "Sample PDF must exist for test"
    
    extractor = PDFTextExtractor("test_job_1")
    pages = extractor.extract_text_pages(sample_pdf)
    
    assert len(pages) == 2, "Expected 2 pages in sample PDF"
    assert "DEFAULT AIS" in pages[0]["text"]
    assert "AI1.1" in pages[0]["text"]
    assert "DEFAULT PIDCON" in pages[1]["text"]
    assert "PIDCON1" in pages[1]["text"]
