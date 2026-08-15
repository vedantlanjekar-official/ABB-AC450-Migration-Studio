"""
grammar_parser.py - Stage 4 & 5: Engineering Grammar & Classification of ABB PC Element I/O References.

Supports only the eight required I/O families:
  AI, AO, DI, DO, AI800, AO800, DI800, DO800.

Reference formats handled:
  Standard:       =AI1.1/940LC391.MV
  800-Series:     =AI800_1.1/940LC391.MV
  Channel+Port:   =AI800_22.5:22/M49FI1201.MV:ERR
  P-prefix:       P-=AO0191/M49ARA104.CA41
"""

from typing import Optional, List, Tuple, Dict
import re
from pydantic import BaseModel, Field


class ParsedIOReference(BaseModel):
    io_family: str        # e.g., "AI800_", "AI", "AO", "DI", "DO"
    io_type: str          # Simplified family used for sorting/grouping
    category: str         # Excel Category code: AI, AO, AI800, etc.
    card_number: int
    channel_number: int   # 0 if no channel specified
    loop_tag: str
    device_tag: str
    source_reference: str
    page_number: int = 1


class GrammarParser:
    """Engineering Grammar Parser for ABB AC450 PC Element I/O References."""

    # (io_family, io_type, category_code) — only the eight supported I/O families
    PREFIX_MAP: Dict[str, Tuple[str, str, str]] = {
        "AI800_": ("AI800_", "AI", "AI800"),
        "AO800_": ("AO800_", "AO", "AO800"),
        "DI800_": ("DI800_", "DI", "DI800"),
        "DO800_": ("DO800_", "DO", "DO800"),
        "AI800":  ("AI800_", "AI", "AI800"),
        "AO800":  ("AO800_", "AO", "AO800"),
        "DI800":  ("DI800_", "DI", "DI800"),
        "DO800":  ("DO800_", "DO", "DO800"),
        "AI":     ("AI", "AI", "AI"),
        "AO":     ("AO", "AO", "AO"),
        "DI":     ("DI", "DI", "DI"),
        "DO":     ("DO", "DO", "DO"),
    }

    _PREFIX_ORDER = [
        "AI800_", "AO800_", "DI800_", "DO800_",
        "AI800", "AO800", "DI800", "DO800",
        "AI", "AO", "DI", "DO",
    ]

    _PREFIX_ALT = (
        r'AI800_|AO800_|DI800_|DO800_|'
        r'AI800|AO800|DI800|DO800|'
        r'AI|AO|DI|DO'
    )

    _DEVICE_TAG = r'''
        (?P<device_tag>
            [A-Za-z0-9_][A-Za-z0-9_\-]*
            (?:\.[A-Za-z0-9_]+)*
            (?::[A-Za-z0-9_]+)?
        )
        (?![A-Za-z0-9_.])
    '''

    _LEADING_NOISE = re.compile(
        r'^(?:[-+]?\s*P\s*-?\s*=?\s*|[=+\-]+\s*)+',
        re.IGNORECASE
    )

    # Pattern 0 (most specific): CARD.CHANNEL:TERMINAL/TAG
    # Example: =AI800_22.5:22/M49FI1201.MV:ERR
    PATTERN_CHANNEL_PORT = re.compile(
        rf'''
        (?P<prefix>{_PREFIX_ALT})
        \s*_?\s*
        (?P<card>\d{{1,4}})
        \s*\.\s*
        (?P<channel>\d{{1,3}})
        \s*:\s*
        (?P<terminal>\d{{1,4}})
        \s*[/]\s*
        {_DEVICE_TAG}
        ''',
        re.VERBOSE | re.IGNORECASE
    )

    # Pattern 1: Standard & 800-Series — PREFIX{CARD}.{CHANNEL}/{DEVICE_TAG}
    PATTERN_STANDARD = re.compile(
        rf'''
        (?P<prefix>{_PREFIX_ALT})
        \s*_?\s*
        (?P<card>\d{{1,4}})
        \s*\.\s*
        (?P<channel>\d{{1,3}})
        \s*[/]\s*
        {_DEVICE_TAG}
        ''',
        re.VERBOSE | re.IGNORECASE
    )

    # Pattern 2: Port-style — PREFIX{CARD}:{PORT}/{DEVICE_TAG}
    PATTERN_PORT = re.compile(
        rf'''
        (?P<prefix>{_PREFIX_ALT})
        \s*
        (?P<card>\d{{1,4}})
        \s*:\s*
        (?P<port>\d{{1,4}})
        \s*[/]\s*
        {_DEVICE_TAG}
        ''',
        re.VERBOSE | re.IGNORECASE
    )

    # Pattern 3: No-channel — PREFIX{CARD}/{DEVICE_TAG}
    PATTERN_NO_CHANNEL = re.compile(
        rf'''
        (?P<prefix>{_PREFIX_ALT})
        \s*
        (?P<card>\d{{1,4}})
        \s*[/]\s*
        {_DEVICE_TAG}
        ''',
        re.VERBOSE | re.IGNORECASE
    )

    @classmethod
    def normalize_candidate(cls, candidate: str) -> str:
        """Strip diagram prefixes (P-, -P-, =) so the grammar can match cleanly."""
        text = candidate.strip()
        text = cls._LEADING_NOISE.sub('', text).strip()
        return text

    @classmethod
    def parse_reference(cls, candidate: str, page_number: int = 1) -> Optional[ParsedIOReference]:
        """Parses the first valid I/O reference from a candidate string."""
        refs = cls.parse_all_references(candidate, page_number=page_number)
        return refs[0] if refs else None

    @classmethod
    def parse_all_references(
        cls, candidate: str, page_number: int = 1
    ) -> List[ParsedIOReference]:
        """
        Extract every valid I/O reference from a candidate string.

        Dense spatial bands and fused CAD lines often contain multiple refs;
        returning only the first match silently drops the rest.
        """
        raw = candidate.strip()
        cleaned = cls.normalize_candidate(raw)
        if not cleaned:
            return []

        found: List[ParsedIOReference] = []
        occupied: List[Tuple[int, int]] = []

        pattern_specs = (
            (cls.PATTERN_CHANNEL_PORT, "channel"),
            (cls.PATTERN_STANDARD, "channel"),
            (cls.PATTERN_PORT, "port"),
            (cls.PATTERN_NO_CHANNEL, "zero"),
        )

        for pattern, channel_mode in pattern_specs:
            for match in pattern.finditer(cleaned):
                span = match.span()
                if any(not (span[1] <= a or span[0] >= b) for a, b in occupied):
                    continue
                if channel_mode == "channel":
                    channel_str = match.group("channel")
                elif channel_mode == "port":
                    channel_str = match.group("port")
                else:
                    channel_str = "0"

                ref = cls._build_reference(
                    match.group("prefix"),
                    match.group("card"),
                    channel_str,
                    match.group("device_tag"),
                    raw[span[0]:span[1]] if span[1] <= len(raw) else match.group(0),
                    page_number,
                )
                if ref:
                    found.append(ref)
                    occupied.append(span)

        return found

    @classmethod
    def _build_reference(
        cls,
        raw_prefix: str,
        card_str: str,
        channel_str: str,
        device_tag_raw: str,
        source: str,
        page_number: int
    ) -> Optional[ParsedIOReference]:
        """Builds a ParsedIOReference from matched groups."""

        prefix_upper = raw_prefix.upper()
        prefix_info = None
        for key in cls._PREFIX_ORDER:
            key_u = key.upper()
            if prefix_upper == key_u or prefix_upper == key_u.rstrip('_') or (
                key_u.endswith('_') and prefix_upper + '_' == key_u
            ):
                prefix_info = cls.PREFIX_MAP[key]
                break

        if not prefix_info:
            return None

        io_family, io_type, category = prefix_info

        try:
            card_num = int(card_str)
            chan_num = int(channel_str)
        except ValueError:
            return None

        # Keep the complete device tag, including colon attributes (:SELECTED, :MAN, :ERR).
        dev_tag = cls.clean_device_tag(device_tag_raw)

        if not re.search(r'[A-Z]', dev_tag) or len(dev_tag) < 3:
            return None

        loop_tag = cls.derive_loop_tag(dev_tag)

        if not re.search(r'[A-Z]', loop_tag):
            return None

        return ParsedIOReference(
            io_family=io_family,
            io_type=io_type,
            category=category,
            card_number=card_num,
            channel_number=chan_num,
            loop_tag=loop_tag,
            device_tag=dev_tag,
            source_reference=source,
            page_number=page_number
        )

    @classmethod
    def clean_device_tag(cls, device_tag: str) -> str:
        """Return the Device Tag exactly as printed — no length or suffix limits.

        Normalization only:
          1. Uppercase
          2. Trim whitespace / trailing punctuation
          3. Discard colon attributes (:MAN, :ERR, :SELECTED, …)
          4. Keep every letter/digit/_/-/. up to the first true delimiter

        Does NOT use predefined suffix lists and does NOT impose a maximum length.
        """
        tag = (device_tag or "").strip().upper()
        if not tag:
            return ""

        # Operating states / modes after a colon are not part of the Device Tag
        if ":" in tag:
            tag = tag.split(":", 1)[0]

        tag = tag.strip().rstrip(".,; ")

        # Capture the complete engineering identifier — unlimited length
        m = re.match(r"^([A-Z0-9][A-Z0-9_\-]*(?:\.[A-Z0-9_\-]*)*)", tag)
        if not m:
            return tag
        # Trim trailing structural punctuation only. Trailing underscores are
        # PRESERVED because ABB AAX exports use IT_, ST_, INT_, SSP_, CSP_
        # (etc.) as legitimate suffixes that are semantically distinct from
        # their underscore-less variants (IT, ST, INT, SSP, CSP).
        cleaned = m.group(1).rstrip(".-")
        return cleaned

    @classmethod
    def normalize_device_tag(cls, device_tag: str) -> str:
        """Normalized engineering tag (no colon attribute) for loop-tag derivation."""
        return cls.clean_device_tag(device_tag).rstrip(".:")

    @classmethod
    def derive_loop_tag(cls, device_tag: str) -> str:
        """Derives Loop Tag by removing only the final extension after the last period.

        Colon attributes are discarded before derivation:
          940LC391.MV                 -> 940LC391
          949DKA050.KEY:SELECTED      -> 949DKA050
          M49FI1201.MV:ERR            -> M49FI1201
          940M02M1.STRT:MAN           -> 940M02M1
        """
        tag = cls.normalize_device_tag(device_tag)

        if "." in tag:
            return tag.rsplit(".", 1)[0]

        return tag
