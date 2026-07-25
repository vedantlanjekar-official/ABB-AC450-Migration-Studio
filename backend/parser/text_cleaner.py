import re
from typing import List, Tuple
from backend.parser.pdf_loader import PageObject
from backend.core.logging import get_logger

class TextCleaner:
    """
    Stage 2 & Stage 3 — Document Noise Cleaner & Page Merging Module.
    Strips repeated ABB headers, footers, sheet numbers, copyright, and document metadata.
    Merges cleaned lines from all pages into ONE continuous engineering text document.
    """

    NOISE_PATTERNS = [
        re.compile(r'^\s*ABB\s+(?:Automation|Advant|Process|Industry)', re.IGNORECASE),
        re.compile(r'^\s*DATABASE\s+LISTING\b', re.IGNORECASE),
        re.compile(r'^\s*Sheet\s+\d+\b', re.IGNORECASE),
        re.compile(r'^\s*Cont\.\s*\d+\b', re.IGNORECASE),
        re.compile(r'^\s*Page\s+\d+\s+of\s+\d+\b', re.IGNORECASE),
        re.compile(r'^\s*(?:Prepared|Approved|Checked|Dept|Date|Document No)\b', re.IGNORECASE),
        re.compile(r'^\s*Copyright\s+(?:\(c\)|©|\d{4})', re.IGNORECASE),
        re.compile(r'^\s*================================================================================\s*$'),
        re.compile(r'^\s*--------------------------------------------------------------------------------\s*$'),
        re.compile(r'^\s*SYSTEM:\s+.*\s+CONTROLLER:\s+.*$', re.IGNORECASE),
    ]

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def clean_and_merge_pages(self, pages: List[PageObject]) -> Tuple[List[Tuple[int, str]], int]:
        """
        Cleans repeated page metadata and merges pages into ONE continuous line sequence.
        
        Returns:
            Tuple of (List[(page_num, line_str)], ignored_headers_count)
        """
        cleaned_lines: List[Tuple[int, str]] = []
        ignored_count = 0

        for page_obj in pages:
            page_num = page_obj.page_number
            lines = page_obj.raw_text.splitlines()

            for line in lines:
                line_str = line.strip()
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
                    cleaned_lines.append((page_num, line_str))

        self.logger.info(
            f"TextCleaner stripped {ignored_count} header/footer noise lines "
            f"and compiled {len(cleaned_lines)} continuous engineering line(s)."
        )
        return cleaned_lines, ignored_count
