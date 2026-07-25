import re
from typing import List, Tuple
from backend.pc_parser.pdf_reader import PCLineRecord
from backend.core.logging import get_logger

class PCDocumentCleaner:
    """
    PC Element Document Noise Cleaner Module.
    Strips repeated ABB headers, footers, sheet numbers, revision notices, and copyright text.
    """

    NOISE_PATTERNS = [
        re.compile(r'^\s*ABB\s+Automation\b', re.IGNORECASE),
        re.compile(r'^\s*DATABASE\s+LISTING\b', re.IGNORECASE),
        re.compile(r'^\s*Sheet\s+\d+\b', re.IGNORECASE),
        re.compile(r'^\s*Cont\.\s*\d+\b', re.IGNORECASE),
        re.compile(r'^\s*Prepared\b', re.IGNORECASE),
        re.compile(r'^\s*Approved\b', re.IGNORECASE),
        re.compile(r'^\s*Based\s+on\b', re.IGNORECASE),
        re.compile(r'^\s*Project\s+name\b', re.IGNORECASE),
        re.compile(r'^\s*Document\s+number\b', re.IGNORECASE),
        re.compile(r'^\s*Rev\.\s*ind\b', re.IGNORECASE),
        re.compile(r'^\s*Lang\.\b', re.IGNORECASE),
        re.compile(r'^\s*Doc\.\s*des\.\b', re.IGNORECASE),
        re.compile(r'^\s*Resp\.\s*dept\.\b', re.IGNORECASE),
        re.compile(r'^\s*Item\s+des\.\b', re.IGNORECASE),
        re.compile(r'We reserve all rights in this document', re.IGNORECASE),
        re.compile(r'without express authority is strictly forbidden', re.IGNORECASE),
        re.compile(r'©\s*ABB\s+Automation', re.IGNORECASE),
    ]

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def clean_records(self, records: List[PCLineRecord]) -> Tuple[List[PCLineRecord], int]:
        """Cleans document noise lines and returns remaining line records with count of stripped lines."""
        cleaned: List[PCLineRecord] = []
        ignored_count = 0

        for rec in records:
            if self.is_noise(rec.text):
                ignored_count += 1
            else:
                cleaned.append(rec)

        self.logger.info(f"PCDocumentCleaner stripped {ignored_count} noise line(s), leaving {len(cleaned)} engineering line(s).")
        return cleaned, ignored_count

    def is_noise(self, line: str) -> bool:
        line_str = line.strip()
        if not line_str:
            return True
        for pattern in self.NOISE_PATTERNS:
            if pattern.search(line_str):
                return True
        return False
