"""
grammar_parser.py - Stage 4 & 5: Engineering Grammar & Classification of ABB PC Element I/O References.

Supports all ABB AC450 PC Element categories including 800-Series, standard I/O, and
extended controller module types (AOC, AIC, ACC, DOC, DIC, AICT, DICT).

Reference formats handled:
  Standard:       =AI1.1/940LC391.MV
  800-Series:     =AI800_1.1/940LC391.MV
  Channel+Port:   =AI800_22.5:22/M49FI1201.MV:ERR
  Port-style:     =AOC264:17/949DKA050.KEY:SELECTED
  No-channel:     =AOC264/949DKA050.KEY
  P-prefix:       P-=AO0191/M49ARA104.CA41
"""

from typing import Optional, List, Tuple, Dict
import re
from pydantic import BaseModel, Field


class ParsedIOReference(BaseModel):
    io_family: str        # e.g., "AI800_", "AOC", "AI", "AO", "DI", "DO"
    io_type: str          # Simplified family used for sorting/grouping
    category: str         # Excel Category code: AI, AO, AI800, AOC, etc.
    card_number: int
    channel_number: int   # 0 if no channel specified (e.g., =AOC264/tag)
    loop_tag: str
    device_tag: str
    source_reference: str
    page_number: int = 1


class GrammarParser:
    """Engineering Grammar Parser for ABB AC450 PC Element I/O References."""

    # (io_family, io_type, category_code)
    PREFIX_MAP: Dict[str, Tuple[str, str, str]] = {
        "AI800_": ("AI800_", "AI", "AI800"),
        "AO800_": ("AO800_", "AO", "AO800"),
        "DI800_": ("DI800_", "DI", "DI800"),
        "DO800_": ("DO800_", "DO", "DO800"),
        "AI800":  ("AI800_", "AI", "AI800"),
        "AO800":  ("AO800_", "AO", "AO800"),
        "DI800":  ("DI800_", "DI", "DI800"),
        "DO800":  ("DO800_", "DO", "DO800"),
        "AICT":   ("AICT", "AICT", "AICT"),
        "DICT":   ("DICT", "DICT", "DICT"),
        "AOC":    ("AOC", "AOC", "AOC"),
        "ACC":    ("ACC", "ACC", "ACC"),
        "AIC":    ("AIC", "AIC", "AIC"),
        "DOC":    ("DOC", "DOC", "DOC"),
        "DIC":    ("DIC", "DIC", "DIC"),
        "AI":     ("AI", "AI", "AI"),
        "AO":     ("AO", "AO", "AO"),
        "DI":     ("DI", "DI", "DI"),
        "DO":     ("DO", "DO", "DO"),
    }

    _PREFIX_ORDER = [
        "AI800_", "AO800_", "DI800_", "DO800_",
        "AI800", "AO800", "DI800", "DO800",
        "AICT", "DICT",
        "AOC", "ACC", "AIC", "DOC", "DIC",
        "AI", "AO", "DI", "DO",
    ]

    _PREFIX_ALT = (
        r'AI800_|AO800_|DI800_|DO800_|'
        r'AI800|AO800|DI800|DO800|'
        r'AICT|DICT|AOC|ACC|AIC|DOC|DIC|'
        r'AI|AO|DI|DO'
    )

    _DEVICE_TAG = r'''
        (?P<device_tag>
            [A-Za-z0-9_][A-Za-z0-9_\-]*
            (?:\.[A-Za-z0-9_]+)?
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
        """Parses a raw reference string into a structured ParsedIOReference object."""

        raw = candidate.strip()
        cleaned = cls.normalize_candidate(raw)
        if not cleaned:
            return None

        # Pattern 0: CARD.CHANNEL:TERMINAL/TAG  (must run before standard)
        match = cls.PATTERN_CHANNEL_PORT.search(cleaned)
        if match:
            return cls._build_reference(
                match.group("prefix"),
                match.group("card"),
                match.group("channel"),
                match.group("device_tag"),
                raw,
                page_number
            )

        # Pattern 1: CARD.CHANNEL/TAG
        match = cls.PATTERN_STANDARD.search(cleaned)
        if match:
            return cls._build_reference(
                match.group("prefix"),
                match.group("card"),
                match.group("channel"),
                match.group("device_tag"),
                raw,
                page_number
            )

        # Pattern 2: CARD:PORT/TAG
        match = cls.PATTERN_PORT.search(cleaned)
        if match:
            return cls._build_reference(
                match.group("prefix"),
                match.group("card"),
                match.group("port"),
                match.group("device_tag"),
                raw,
                page_number
            )

        # Pattern 3: CARD/TAG
        match = cls.PATTERN_NO_CHANNEL.search(cleaned)
        if match:
            return cls._build_reference(
                match.group("prefix"),
                match.group("card"),
                "0",
                match.group("device_tag"),
                raw,
                page_number
            )

        return None

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
        """Uppercase and isolate a valid engineering device tag from CAD glue.

        Canonical form: LOOP.EXT or LOOP.EXT:ATTR using known ABB extensions.
        """
        tag = device_tag.strip().upper().rstrip(".,;")

        # Longest/most-specific extensions first
        m = re.match(
            r'^([A-Z0-9_]+\.(?:CA\d{1,2}|KEY\d?|CURR|OUT|MV|SEL|PWR|RUN|STOP|IT|RDY|MSTR|[A-Z]{2,4}))'
            r'(?::(SELECTED|MAN|CALC_VAL|ERR|HL|LL|OV|[A-Z_]{2,12}))?',
            tag,
        )
        if m:
            base = m.group(1)
            attr = m.group(2)
            return f"{base}:{attr}" if attr else base

        return tag

    @classmethod
    def normalize_device_tag(cls, device_tag: str) -> str:
        """Base device tag without colon attribute — used only for loop-tag derivation."""
        tag = cls.clean_device_tag(device_tag)
        if ':' in tag:
            tag = tag.split(':', 1)[0]
        return tag.rstrip('.:')

    @classmethod
    def derive_loop_tag(cls, device_tag: str) -> str:
        """Derives Loop Tag by removing only the final extension after the last period.

        Colon attributes are ignored for loop derivation:
          940LC391.MV                 -> 940LC391
          949DKA050.KEY:SELECTED      -> 949DKA050
          M49FI1201.MV:ERR            -> M49FI1201
        """
        tag = cls.normalize_device_tag(device_tag)

        if '.' in tag:
            return tag.rsplit('.', 1)[0]

        return tag
