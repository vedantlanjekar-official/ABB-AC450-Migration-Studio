"""
description_mapper.py - Map loop tags to engineering descriptions from PC diagrams.

Sources (never invents text):
  1. Explicit TAG description / description (TAG) patterns
  2. Adjacent line context near a loop-tag occurrence
  3. Spatial neighbors of I/O word tokens on the same drawing band
"""

from typing import Dict, List, Optional, Any
import re


class DescriptionMapper:
    """Finds engineering descriptions for loop tags from diagram text."""

    TAG_TOKEN = r'(?:[0-9]{2,4}[A-Z]{1,4}[0-9]{1,4}|[A-Z]\d{2}[A-Z0-9_]{2,12})'

    INVALID_DESC_KEYWORDS = [
        "EXECUTION ORDER", "MOVE", "SHEET", "REV", "ABB", "COMMON IDENTITY",
        "DIAGRAM", "CONTROL SYSTEM", "CONVERT", "PAGE", "PC32", "PCPGM",
        "CONTRM", "FUNCM", "BLOCK", "PREPARED", "DOC. DES", "ITEM DES",
        "RESERVE ALL RIGHTS", "REPRODUCTION", "FORBIDDEN", "AUTOMATION",
        "SELECTED", "CALC_VAL", "REM", "ACT", "BALREF", "REG-RET",
    ]

    @classmethod
    def build_description_map(
        cls,
        page_texts: List[str],
        pages_words: Optional[List[List[Dict[str, Any]]]] = None,
    ) -> Dict[str, str]:
        """Build loop_tag -> description map from all pages."""
        desc_map: Dict[str, str] = {}

        TAG_DESC_PATTERN = re.compile(
            rf'\b(?P<tag>{cls.TAG_TOKEN})\b(?:\s*[:\-–]\s*|\s+)(?P<desc>[A-Za-z][A-Za-z0-9\s/#.]{{2,50}})',
            re.IGNORECASE,
        )
        REVERSE_PATTERN = re.compile(
            rf'\b(?P<desc>[A-Za-z][A-Za-z0-9\s/#.]{{2,50}})\s*\((?P<tag>{cls.TAG_TOKEN})\)',
            re.IGNORECASE,
        )

        for page_text in page_texts:
            for line in [ln.strip() for ln in page_text.splitlines() if ln.strip()]:
                match = TAG_DESC_PATTERN.search(line)
                if match:
                    tag = match.group("tag").upper()
                    desc = match.group("desc").strip()
                    if not cls._is_invalid_description(desc):
                        desc_map.setdefault(tag, desc)

                match_rev = REVERSE_PATTERN.search(line)
                if match_rev:
                    tag = match_rev.group("tag").upper()
                    desc = match_rev.group("desc").strip()
                    if not cls._is_invalid_description(desc):
                        desc_map.setdefault(tag, desc)

        # Spatial annotations near tokens that look like loop tags
        if pages_words:
            for words in pages_words:
                spatial = cls._spatial_tag_descriptions(words)
                for tag, desc in spatial.items():
                    desc_map.setdefault(tag, desc)

        return desc_map

    @classmethod
    def _spatial_tag_descriptions(cls, words: List[Dict[str, Any]]) -> Dict[str, str]:
        """Associate alphabetic labels near loop-tag-like tokens on the same band."""
        result: Dict[str, str] = {}
        if not words:
            return result

        tag_re = re.compile(rf'(?i)^(?P<tag>{cls.TAG_TOKEN})(?:\.[A-Z0-9_]+)?$')

        for w in words:
            text = str(w.get("text", "")).strip()
            m = tag_re.match(text)
            if not m:
                # Also accept device tags inside I/O strings
                if "/" in text:
                    tail = text.split("/")[-1]
                    base = tail.split(":")[0]
                    if "." in base:
                        base = base.rsplit(".", 1)[0]
                    if re.match(rf'(?i)^{cls.TAG_TOKEN}$', base):
                        tag = base.upper()
                    else:
                        continue
                else:
                    continue
            else:
                tag = m.group("tag").upper()

            y = (w.get("top", 0) + w.get("bottom", 0)) / 2
            x0 = w.get("x0", 0)
            neighbors: List[str] = []
            for w2 in words:
                t2 = str(w2.get("text", "")).strip()
                if not t2 or t2 == text:
                    continue
                y2 = (w2.get("top", 0) + w2.get("bottom", 0)) / 2
                if abs(y2 - y) > 5:
                    continue
                # Prefer labels to the left of the tag (common on drawings)
                if w2.get("x1", 0) > x0 + 5:
                    continue
                if cls._is_invalid_description(t2):
                    continue
                if re.search(r'[A-Za-z]{3,}', t2):
                    neighbors.append(t2)

            if neighbors:
                desc = " ".join(neighbors[-4:]).strip()
                if not cls._is_invalid_description(desc):
                    result.setdefault(tag, desc)

        return result

    @classmethod
    def find_description_for_tag(
        cls,
        loop_tag: str,
        page_text: str,
        desc_map: Dict[str, str],
        page_words: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Find description for a loop tag using map, page context, then spatial words."""
        tag_upper = loop_tag.upper()

        if tag_upper in desc_map:
            return desc_map[tag_upper]

        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if tag_upper not in line.upper():
                continue

            clean_line = re.sub(
                r'\b' + re.escape(tag_upper) + r'[^\s]*',
                '',
                line,
                flags=re.IGNORECASE,
            ).strip()
            clean_line = clean_line.lstrip("-:=").strip()
            if len(clean_line) >= 3 and not cls._is_invalid_description(clean_line):
                return clean_line

            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                if len(next_line) >= 3 and not cls._is_invalid_description(next_line):
                    if not re.search(r'\b(?:AI800|AO800|DI800|DO800|AI|AO|DI|DO)', next_line, re.IGNORECASE):
                        return next_line

        if page_words:
            spatial = cls._spatial_tag_descriptions(page_words)
            if tag_upper in spatial:
                return spatial[tag_upper]

        return ""

    @classmethod
    def _is_invalid_description(cls, text: str) -> bool:
        upper = text.upper().strip()

        if len(upper) < 3 or len(upper) > 80:
            return True

        if re.search(r'\b(?:AI800|AO800|DI800|DO800|AI|AO|DI|DO)\b', upper):
            return True

        for kw in cls.INVALID_DESC_KEYWORDS:
            if kw in upper:
                return True

        if upper.startswith("D=") or "IA2" in upper or re.search(r'D\s*=\s*-?\d+', upper):
            return True

        if re.search(r'\([A-Z0-9\s,]+\)', upper):
            return True

        if "/" in upper or re.search(r':\d+', upper):
            return True

        if re.match(r'^[A-Z]?[0-9]{2,4}[A-Z0-9_]+$', upper):
            return True

        letters = re.findall(r'[A-Za-z]', upper)
        if len(letters) < 3:
            return True

        return False
