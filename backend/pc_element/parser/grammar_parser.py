"""
grammar_parser.py - Stage 4 & 5: Engineering Grammar & Classification of ABB Hardwired I/O References.
Supports 800-Series fixed module keywords (AI800_, AO800_, DI800_, DO800_) and standard I/O series.
"""

from typing import Optional, List, Tuple, Dict
import re
from pydantic import BaseModel, Field


class ParsedIOReference(BaseModel):
    io_family: str        # e.g., "AI800_", "AO800_", "DI800_", "DO800_", "AI", "AO", "DI", "DO"
    io_type: str          # "AI", "AO", "DI", "DO"
    category: str         # "Analog Input", "Analog Output", "Digital Input", "Digital Output"
    card_number: int
    channel_number: int
    loop_tag: str
    device_tag: str
    source_reference: str
    page_number: int = 1


class GrammarParser:
    """Engineering Grammar Parser for ABB AC450 Hardwired I/O References."""

    PREFIX_MAP: Dict[str, Tuple[str, str, str]] = {
        "AI800_": ("AI800_", "AI", "Analog Input"),
        "AO800_": ("AO800_", "AO", "Analog Output"),
        "DI800_": ("DI800_", "DI", "Digital Input"),
        "DO800_": ("DO800_", "DO", "Digital Output"),
        "AI800": ("AI800_", "AI", "Analog Input"),
        "AO800": ("AO800_", "AO", "Analog Output"),
        "DI800": ("DI800_", "DI", "Digital Input"),
        "DO800": ("DO800_", "DO", "Digital Output"),
        "AI": ("AI", "AI", "Analog Input"),
        "AO": ("AO", "AO", "Analog Output"),
        "DI": ("DI", "DI", "Digital Input"),
        "DO": ("DO", "DO", "Digital Output"),
    }

    # Master Regular Expression matching 800-Series and Standard I/O references.
    # Accepts optional leading [-=], matches card, channel, and device_tag containing letters.
    MASTER_IO_PATTERN = re.compile(
        r'''[-=]?\s*
        (?P<prefix>AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)
        \s*_?\s*
        (?P<card>\d{1,3})
        \s*\.\s*
        (?P<channel>\d{1,3})
        \s*[/:\s=]\s*
        (?P<device_tag>[A-Za-z0-9_\-]*[A-Za-z][A-Za-z0-9_\-]*(?:\.[A-Za-z0-9_\-]+)*)
        ''',
        re.VERBOSE | re.IGNORECASE
    )

    @classmethod
    def parse_reference(cls, candidate: str, page_number: int = 1) -> Optional[ParsedIOReference]:
        """Executes engineering extraction pipeline on raw reference strings (e.g., -AI800_2.1/M49M021.CURR or AI800_1.16/82M073.IT)."""
        clean_cand = candidate.strip().lstrip('-=*:/ \t').strip()

        match = cls.MASTER_IO_PATTERN.search(candidate.strip())
        if not match:
            match = cls.MASTER_IO_PATTERN.search(clean_cand)

        if not match:
            return None

        raw_prefix_match = match.group("prefix")
        matched_prefix_upper = raw_prefix_match.upper()

        prefix_info = None
        for p_key, (canonical_family, io_type, category) in cls.PREFIX_MAP.items():
            if matched_prefix_upper == p_key or matched_prefix_upper == p_key.rstrip('_'):
                prefix_info = (canonical_family, io_type, category)
                break

        if not prefix_info:
            return None

        io_family, io_type, category = prefix_info

        card_str = match.group("card")
        chan_str = match.group("channel")
        dev_tag = match.group("device_tag").strip().upper()

        try:
            card_num = int(card_str)
            chan_num = int(chan_str)
        except ValueError:
            return None

        # Verify device_tag contains at least one letter and is at least 3 chars
        if not re.search(r'[A-Z]', dev_tag) or len(dev_tag) < 3:
            return None

        loop_tag = cls.derive_loop_tag(dev_tag)

        # Verify loop_tag contains at least one letter
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
            source_reference=candidate.strip(),
            page_number=page_number
        )

    @classmethod
    def derive_loop_tag(cls, device_tag: str) -> str:
        """Derives Loop Tag by removing only the final extension.
        Example: 82M073.IT -> 82M073
        Example: 82LIC660.MV -> 82LIC660
        Example: 82LIC660.OUT -> 82LIC660
        Example: M49M021.CURR -> M49M021
        """
        if '.' in device_tag:
            parts = device_tag.rsplit('.', 1)
            return parts[0]
        return device_tag
