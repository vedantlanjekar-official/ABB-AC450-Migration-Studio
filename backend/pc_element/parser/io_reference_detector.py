"""
io_reference_detector.py - Multi-strategy I/O candidate detection.

Strategies:
  1. Regex scan across keyword-filtered lines / text layers
  2. Spatial token assembly from word coordinates
  3. Line-pair stitching for split PREFIX / TAG forms

NOTE: Patterns are intentionally ReDoS-safe. Nested `*` lead groups previously
hung the production worker on large DB-style PDF text blobs.
"""

from typing import List, Set, Dict, Any, Optional
import re

from backend.pc_element.parser.token_assembler import TokenAssembler


class IOReferenceDetector:
    """Multi-strategy scanner for ABB AC450 PC Element I/O candidates."""

    _PREFIXES = (
        r'AI800_|AO800_|DI800_|DO800_|'
        r'AI800|AO800|DI800|DO800|'
        r'AI|AO|DI|DO'
    )

    # Single optional lead fragment — must NOT use nested star quantifiers.
    _LEAD = r'(?:[+\-=P\s]{0,8})?'
    # Detection-side tag — no character-length caps; stop only at delimiters.
    _TAG = (
        r'[A-Za-z0-9_][A-Za-z0-9_\-]*'
        r'(?:\.[A-Za-z0-9_]+)*'
        r'(?::[A-Za-z0-9_]+)?'
    )

    PATTERN_CHANNEL_PORT = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')_?\d{1,4}\.\d{1,3}:\d{1,4}/' + _TAG,
        re.IGNORECASE,
    )
    PATTERN_STANDARD = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')_?\d{1,4}\.\d{1,3}/' + _TAG,
        re.IGNORECASE,
    )
    PATTERN_PORT = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')\d{1,4}:\d{1,4}/' + _TAG,
        re.IGNORECASE,
    )
    PATTERN_NO_CHANNEL = re.compile(
        _LEAD + r'(?:' + _PREFIXES + r')\d{1,4}/' + _TAG,
        re.IGNORECASE,
    )

    ALL_PATTERNS = (
        PATTERN_CHANNEL_PORT,
        PATTERN_STANDARD,
        PATTERN_PORT,
        PATTERN_NO_CHANNEL,
    )

    KEYWORD_REGEX = re.compile(
        r'\b(?:AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)\b',
        re.IGNORECASE,
    )
    # Require I/O-like prefix near a slash before treating "/" alone as a scan trigger
    IO_NEAR_SLASH = re.compile(
        r'(?:AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)'
        r'.{0,24}/',
        re.IGNORECASE,
    )
    FRAG_PREFIX = re.compile(
        r'(?ix)(?:P-?)?[=-]?(?:' + _PREFIXES + r')_?'
        r'(\d{1,4}(?:[.:]\d{1,4}(?::\d{1,4})?)?)'
    )
    FRAG_TAG = re.compile(
        r'(?ix)^\s*/\s*([A-Za-z0-9_][A-Za-z0-9_\-.]*'
        r'(?::[A-Za-z0-9_]+)?)'
    )

    # Hard caps to keep production memory/CPU bounded on free-tier hosts.
    MAX_SOURCE_CHARS = 20000
    MAX_LINE_CHARS = 500

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

        # Prefer short line sources; never scan giant fused CAD blobs whole.
        sources: List[str] = []
        for line in lines or []:
            line_str = (line or "").strip()
            if not line_str:
                continue
            # Split overlong fused CAD lines instead of skipping them entirely
            chunks = [line_str]
            if len(line_str) > cls.MAX_LINE_CHARS:
                chunks = re.split(r'(?=(?:[=+\-]|\bP-))', line_str)
            for chunk in chunks:
                chunk = (chunk or "").strip()
                if not chunk or len(chunk) > cls.MAX_LINE_CHARS:
                    continue
                if cls.KEYWORD_REGEX.search(chunk) or cls.IO_NEAR_SLASH.search(chunk):
                    sources.append(chunk)

        # Optionally add truncated page text only if keyword hits exist.
        page_str = (page_text or "").strip()
        if page_str and cls.KEYWORD_REGEX.search(page_str):
            sources.append(page_str[: cls.MAX_SOURCE_CHARS])

        if text_layers:
            for name, blob in text_layers.items():
                # Include words_joined — spatial layer is handled via TokenAssembler
                if name == "spatial":
                    continue
                blob_str = (blob or "").strip()
                if not blob_str or not cls.KEYWORD_REGEX.search(blob_str):
                    continue
                sources.append(blob_str[: cls.MAX_SOURCE_CHARS])

        for text_str in sources:
            for pattern in cls.ALL_PATTERNS:
                for m in pattern.finditer(text_str):
                    cleaned = m.group(0).strip().rstrip(".,;")
                    if len(cleaned) >= 5 and "/" in cleaned:
                        candidates.add(cleaned)

        # Line-pair stitching: PREFIX addr on one line, /TAG on next
        for i, line in enumerate(lines or []):
            pm = cls.FRAG_PREFIX.search(line or "")
            if not pm:
                continue
            if "/" in (line or "")[pm.end(): pm.end() + 3]:
                continue
            for j in range(i + 1, min(i + 3, len(lines))):
                tm = cls.FRAG_TAG.match(lines[j] or "")
                if tm:
                    stitched = f"{(line or '').strip()}{(lines[j] or '').strip()}"
                    if len(stitched) >= 5 and "/" in stitched:
                        candidates.add(stitched)
                    break

        # Spatial assembly from word coordinates (bounded)
        if words:
            try:
                for cand in TokenAssembler.assemble_candidates(words[:5000]):
                    cleaned = (cand or "").strip().rstrip(".,;")
                    if len(cleaned) >= 5 and "/" in cleaned and cls.KEYWORD_REGEX.search(cleaned):
                        candidates.add(cleaned)
            except Exception as exc:
                import logging
                logging.getLogger("pc_element_parser").warning(
                    "Spatial token assembly failed: %s", exc
                )

        return sorted(c for c in candidates if len(c) >= 5)
