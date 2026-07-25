import re
from typing import List, Tuple
from backend.core.logging import get_logger

class HeaderFooterFilter:
    """
    Detects and filters out repeated ABB page headers, footers, sheet numbers,
    approval metadata blocks, copyright notices, and document control metadata.
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

    def filter_lines(self, line_stream: List[Tuple[int, int, str]]) -> Tuple[List[Tuple[int, int, str]], int]:
        """
        Filters out page headers/footers from the line stream.
        
        Args:
            line_stream: List of (page_num, line_idx, line_text)
            
        Returns:
            Tuple of (cleaned_line_stream, ignored_lines_count)
        """
        cleaned: List[Tuple[int, int, str]] = []
        ignored_count = 0

        for page_num, idx, line in line_stream:
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
                cleaned.append((page_num, idx, line))

        self.logger.info(f"HeaderFooterFilter ignored {ignored_count} PDF header/footer noise line(s).")
        return cleaned, ignored_count
