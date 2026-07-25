"""
io_reference_detector.py - Stage 3: Full page scanning for hardwired I/O candidate strings.
Scans all page coordinates regardless of layout position.
"""

from typing import List, Set
import re


class IOReferenceDetector:
    """Scans page lines and text for potential hardwired I/O candidate strings."""

    # Candidate regex matching `-AI800_2.1/M49M021.CURR`, `AI800_ 2.1/M49M021.CURR`, `=AI800_22.5/M49FI1201.MV`
    CANDIDATE_REGEX = re.compile(
        r'[-=]?\s*(?:AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)\s*_?\s*\d+\s*\.\s*\d+\s*[/:\s=]\s*[^\s,()]+',
        re.IGNORECASE
    )

    # General token scanner fallback
    TOKEN_REGEX = re.compile(
        r'[-=]?\s*(?:AI800_|AO800_|DI800_|DO800_|AI|AO|DI|DO)\s*_?\s*\d+\.\d+[^\s,()]*',
        re.IGNORECASE
    )

    @classmethod
    def detect_candidates_in_page(cls, page_text: str, lines: List[str]) -> List[str]:
        """Scans page text and lines, returning a unique list of raw candidate strings."""
        candidates: Set[str] = set()

        # 1. Line-by-line scan (also add full line if line contains I/O keyword)
        for line in lines:
            line_str = line.strip()
            matches = cls.CANDIDATE_REGEX.findall(line_str)
            for m in matches:
                candidates.add(m.strip())

            tokens = cls.TOKEN_REGEX.findall(line_str)
            for t in tokens:
                candidates.add(t.strip())

            if re.search(r'\b(?:AI|AO|DI|DO)(?:800)?\b', line_str, re.IGNORECASE):
                candidates.add(line_str)

        # 2. Entire text blob scan
        blob_matches = cls.CANDIDATE_REGEX.findall(page_text)
        for m in blob_matches:
            candidates.add(m.strip())

        blob_tokens = cls.TOKEN_REGEX.findall(page_text)
        for t in blob_tokens:
            candidates.add(t.strip())

        # Filter candidates
        cleaned_candidates = [c for c in candidates if len(c) >= 5]
        return sorted(cleaned_candidates)
