import re
from typing import List, Tuple
from backend.parser.pdf_reader import LineRecord
from backend.core.logging import get_logger

class DocumentCleaner:
    """
    Stage 2 — Document Metadata Cleaner Module.
    Strips non-engineering metadata lines (ABB Automation, DATABASE LISTING, Sheet numbers, Copyright, etc.).
    Preserves ONLY engineering document node declarations.
    """

    NOISE_PATTERNS = [
        re.compile(r'^\s*ABB\s+(?:Automation|Advant|Process|Industry)', re.IGNORECASE),
        re.compile(r'^\s*DATABASE\s+LISTING\b', re.IGNORECASE),
        re.compile(r'^\s*Sheet\s+\d+\b', re.IGNORECASE),
        re.compile(r'^\s*Cont\.\s*\d+\b', re.IGNORECASE),
        re.compile(r'^\s*Page\s+\d+\s+of\s+\d+\b', re.IGNORECASE),
        re.compile(r'^\s*(?:Prepared|Approved|Checked|Dept|Date|Document No|Document Number|Revision|Language)\b', re.IGNORECASE),
        re.compile(r'^\s*Copyright\s+(?:\(c\)|©|\d{4})', re.IGNORECASE),
        re.compile(r'^\s*================================================================================\s*$'),
        re.compile(r'^\s*--------------------------------------------------------------------------------\s*$'),
        re.compile(r'^\s*SYSTEM:\s+.*\s+CONTROLLER:\s+.*$', re.IGNORECASE),
    ]

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def clean_line_records(self, line_records: List[LineRecord]) -> Tuple[List[LineRecord], int]:
        """Strips document header/footer noise lines."""
        cleaned_records: List[LineRecord] = []
        ignored_count = 0

        for rec in line_records:
            line_str = rec.text.strip()
            if not line_str:
                continue

            is_noise = False
            for pattern in self.NOISE_PATTERNS:
                if pattern.search(line_str):
                    is_noise = True
                    break

            if is_noise:
                ignored_count += 1
            else:
                cleaned_records.append(rec)

        self.logger.info(
            f"DocumentCleaner stripped {ignored_count} metadata noise line(s), leaving {len(cleaned_records)} engineering line(s)."
        )
        return cleaned_records, ignored_count
