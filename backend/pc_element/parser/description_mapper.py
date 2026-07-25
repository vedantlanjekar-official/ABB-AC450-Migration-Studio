"""
description_mapper.py - Stage 6: Map loop tags to engineering descriptions found in the PDF.
Never invents or fabricates descriptions; leaves field blank if no description is present.
"""

from typing import Dict, List, Optional
import re


class DescriptionMapper:
    """Finds engineering descriptions for loop tags from diagram text."""

    INVALID_DESC_KEYWORDS = [
        "EXECUTION ORDER",
        "MOVE",
        "SHEET",
        "REV",
        "ABB",
        "COMMON IDENTITY",
        "DIAGRAM",
        "CONTROL SYSTEM",
        "CONVERT",
        "PAGE"
    ]

    @classmethod
    def build_description_map(cls, page_texts: List[str]) -> Dict[str, str]:
        """Scans all pages in the PDF and builds a dictionary mapping loop_tag -> description."""
        desc_map: Dict[str, str] = {}
        
        TAG_DESC_PATTERN = re.compile(
            r'\b(?P<tag>[0-9]{2,4}[A-Z]{1,4}[0-9]{1,4})\b(?:\s*[:\-–]\s*|\s+)(?P<desc>[A-Za-z0-9\s/]{3,50})',
            re.IGNORECASE
        )
        REVERSE_PATTERN = re.compile(
            r'\b(?P<desc>[A-Za-z0-9\s/]{3,50})\s*\((?P<tag>[0-9]{2,4}[A-Z]{1,4}[0-9]{1,4})\)',
            re.IGNORECASE
        )

        for page_text in page_texts:
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            for line in lines:
                match = TAG_DESC_PATTERN.search(line)
                if match:
                    tag = match.group("tag").upper()
                    desc = match.group("desc").strip()
                    if not cls._is_invalid_description(desc):
                        desc_map[tag] = desc

                match_rev = REVERSE_PATTERN.search(line)
                if match_rev:
                    tag = match_rev.group("tag").upper()
                    desc = match_rev.group("desc").strip()
                    if not cls._is_invalid_description(desc):
                        desc_map[tag] = desc

        return desc_map

    @classmethod
    def find_description_for_tag(cls, loop_tag: str, page_text: str, desc_map: Dict[str, str]) -> str:
        """Finds description for a loop tag using the global map or local page context."""
        tag_upper = loop_tag.upper()

        # 1. Check pre-built global description map
        if tag_upper in desc_map:
            return desc_map[tag_upper]

        # 2. Local page line search near loop tag occurrence
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if tag_upper in line.upper():
                clean_line = re.sub(r'\b' + re.escape(tag_upper) + r'[^\s]*', '', line, flags=re.IGNORECASE).strip()
                clean_line = clean_line.lstrip('-:=').strip()
                if len(clean_line) >= 3 and not cls._is_invalid_description(clean_line):
                    return clean_line

                if idx + 1 < len(lines):
                    next_line = lines[idx + 1]
                    if len(next_line) >= 3 and not cls._is_invalid_description(next_line):
                        if not re.search(r'\b(?:AI|AO|DI|DO)', next_line, re.IGNORECASE):
                            return next_line

        return ""

    @classmethod
    def _is_invalid_description(cls, text: str) -> bool:
        """Filter out strings that are technical tags, parameter blocks, or noise."""
        upper = text.upper().strip()

        # Ignore empty or very short/long strings
        if len(upper) < 3 or len(upper) > 80:
            return True

        # Ignore I/O prefixes
        if re.search(r'\b(?:AI|AO|DI|DO)(?:800)?', upper):
            return True

        # Ignore noise keywords (EXECUTION ORDER, MOVE, SHEET, etc.)
        for kw in cls.INVALID_DESC_KEYWORDS:
            if kw in upper:
                return True

        # Ignore parameter lines (e.g. D=0.000000-12, D=-0.0, D=0-4 24, IA2, 2 R)
        if upper.startswith("D=") or "IA2" in upper or re.search(r'D\s*=\s*-?\d+', upper):
            return True

        # Ignore parenthesized coordinate tuples like (B,8)
        if re.search(r'\([A-Z0-9\s,]+\)', upper):
            return True

        # Require at least 3 letters in a real description (reject pure numbers or math tokens)
        letters = re.findall(r'[A-Za-z]', upper)
        if len(letters) < 3:
            return True

        return False
