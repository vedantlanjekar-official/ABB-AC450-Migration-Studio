"""
io_reference_detector.py - Multi-strategy I/O candidate detection.

Strategies:
  1. Regex scan across all fused text layers
  2. Spatial token assembly from word coordinates
  3. Line-pair stitching for split PREFIX / TAG forms
"""

from typing import List, Set, Dict, Any, Optional
import re

from backend.pc_element.parser.token_assembler import TokenAssembler


class IOReferenceDetector:
    """Multi-strategy scanner for ABB AC450 PC Element I/O candidates."""

    _PREFIXES = (
        r'AI800_|AO800_|DI800_|DO800_|'
        r'AI800|AO800|DI800|DO800|'
        r'AICT|DICT|AOC|ACC|AIC|DOC|DIC|'
        r'AI|AO|DI|DO'
    )

    _LEAD = r'(?:[-+]?\s*P\s*-?\s*=?\s*|[=+\-]+\s*)*'
    _TAG = r'[A-Za-z0-9_][A-Za-z0-9_\-]*(?:\.[A-Za-z0-9_]+)?(?::[A-Za-z0-9_]+)?'

    PATTERN_CHANNEL_PORT = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')\s*_?\s*\d{1,4}\s*\.\s*\d{1,3}\s*:\s*\d{1,4}\s*/\s*' + _TAG,
        re.IGNORECASE,
    )
    PATTERN_STANDARD = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')\s*_?\s*\d{1,4}\s*\.\s*\d{1,3}\s*/\s*' + _TAG,
        re.IGNORECASE,
    )
    PATTERN_PORT = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')\s*\d{1,4}\s*:\s*\d{1,4}\s*/\s*' + _TAG,
        re.IGNORECASE,
    )
    PATTERN_NO_CHANNEL = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')\s*\d{1,4}\s*/\s*' + _TAG,
        re.IGNORECASE,
    )

    ALL_PATTERNS = (
        PATTERN_CHANNEL_PORT,
        PATTERN_STANDARD,
        PATTERN_PORT,
        PATTERN_NO_CHANNEL,
    )

    KEYWORD_REGEX = re.compile(
        r'\b(?:AI|AO|DI|DO|AOC|ACC|AIC|AICT|DOC|DIC|DICT)(?:800)?\b',
        re.IGNORECASE,
    )
    FRAG_PREFIX = re.compile(
        r'(?ix)(?:P\s*-?\s*)?[=-]?\s*(' + _PREFIXES + r')\s*_?\s*'
        r'(\d{1,4}(?:[.:]\d{1,4}(?::\d{1,4})?)?)'
    )
    FRAG_TAG = re.compile(
        r'(?ix)^\s*/\s*([A-Za-z0-9_][A-Za-z0-9_\-.]*(?::[A-Za-z0-9_]+)?)'
    )

    @classmethod
    def detect_candidates_in_page(
        cls,
        page_text: str,
        lines: List[str],
        words: Optional[List[Dict[str, Any]]] = None,
        text_layers: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """Return unique raw candidate strings from all available page signals."""
        candidates: Set[str] = set()

        sources: List[str] = list(lines) + [page_text]
        if text_layers:
            # Skip layers that concatenate CAD glyphs into device tags
            for name, blob in text_layers.items():
                if name in ("words_joined", "spatial"):
                    continue
                sources.append(blob)

        for text in sources:
            text_str = (text or "").strip()
            if not text_str:
                continue
            for pattern in cls.ALL_PATTERNS:
                for m in pattern.findall(text_str):
                    cleaned = m.strip().rstrip(".,;")
                    if len(cleaned) >= 5 and "/" in cleaned:
                        candidates.add(cleaned)

        # Line-pair stitching: PREFIX addr on one line, /TAG on next
        for i, line in enumerate(lines):
            pm = cls.FRAG_PREFIX.search(line or "")
            if not pm:
                continue
            if "/" in (line or "")[pm.end(): pm.end() + 3]:
                continue
            for j in range(i + 1, min(i + 3, len(lines))):
                tm = cls.FRAG_TAG.search(lines[j] or "")
                if tm:
                    candidates.add(f"={pm.group(1)}{pm.group(2)}/{tm.group(1)}")
                    break

        # TokenAssembler reserved for OCR-fragment recovery on low-density pages only
        _ = words

        # Keyword lines as last resort (short lines only)
        for line in lines:
            line_str = (line or "").strip()
            if not line_str or not cls.KEYWORD_REGEX.search(line_str):
                continue
            if "/" not in line_str:
                continue
            embedded = False
            for pattern in cls.ALL_PATTERNS:
                for m in pattern.findall(line_str):
                    cleaned = m.strip().rstrip(".,;")
                    if len(cleaned) >= 5 and "/" in cleaned:
                        candidates.add(cleaned)
                        embedded = True
            if not embedded and len(line_str) < 120:
                candidates.add(line_str)

        return sorted(c for c in candidates if len(c) >= 5)
