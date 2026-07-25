"""
page_cleaner.py - Stage 2: Remove engineering drawing noise while preserving candidate text and title blocks.
"""

from typing import List, Dict, Any, Tuple
import re


class PageCleaner:
    """Cleans page text and extracts drawing header/footer metadata."""

    NOISE_PATTERNS = [
        re.compile(r"We reserve all rights in this document", re.IGNORECASE),
        re.compile(r"in the information contained therein", re.IGNORECASE),
        re.compile(r"Reproduction, use or disclosure to third parties", re.IGNORECASE),
        re.compile(r"without express authority is strictly forbidden", re.IGNORECASE),
        re.compile(r"ABB Industrieschnittstelle", re.IGNORECASE),
        re.compile(r"ABB Automation and Drives", re.IGNORECASE),
        re.compile(r"COMMON IDENTITY:", re.IGNORECASE),
        re.compile(r"Based on\s*:", re.IGNORECASE),
        re.compile(r"Prepared\s*:", re.IGNORECASE),
        re.compile(r"Approved\s*:", re.IGNORECASE),
        re.compile(r"Project name\s*:", re.IGNORECASE),
        re.compile(r"Resp\. dept", re.IGNORECASE),
        re.compile(r"Document number", re.IGNORECASE),
        re.compile(r"Sheet\s+\d+", re.IGNORECASE),
        re.compile(r"Cont\.\s+\d+", re.IGNORECASE),
        re.compile(r"Rev\. ind\.", re.IGNORECASE),
        re.compile(r"Lang\.\s+[E|G|F|S]", re.IGNORECASE),
    ]

    @classmethod
    def is_noise_line(cls, line: str) -> bool:
        """Checks whether a line is purely engineering document frame/copyright noise."""
        clean = line.strip()
        if not clean:
            return True
        for pattern in cls.NOISE_PATTERNS:
            if pattern.search(clean):
                return True
        return False

    @classmethod
    def clean_page_lines(cls, lines: List[str]) -> List[str]:
        """Filters noise lines while retaining text lines containing potential I/O references or metadata."""
        cleaned: List[str] = []
        for line in lines:
            if not cls.is_noise_line(line):
                cleaned.append(line.strip())
        return cleaned
