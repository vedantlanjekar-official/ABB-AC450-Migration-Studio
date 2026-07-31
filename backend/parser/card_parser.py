import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from backend.parser.pdf_reader import LineRecord
from backend.core.logging import get_logger

@dataclass
class CardNode:
    family: str
    card_name: str       # e.g. "AI1", "AI800_1", "AI8001"
    page_number: int
    parameters: Dict[str, Any] = field(default_factory=dict)

class CardParser:
    """
    Stage 5 — Card Definition Node Parser Module.
    Parses Node Type 3 (Card Definitions e.g., AI1 AI, AI800_1 AI810, AI8001 AI800).
    Card Nodes are AST parents holding Card Parameters (:ADDR 32, :CONV_PAR 4..20mA).
    CARD NODES ARE NOT OBJECTS AND ARE NEVER EXPORTED TO EXCEL.
    """

    # Underscore 800-series cards from production DB listings:
    #   AI800_1 AI810, AO800_3 AO810, DI800_2 DI820, DO800_10 DO820
    CARD_800_UNDERSCORE_REGEX = re.compile(
        r'^\s*((?:AI800|AO800|DI800|DO800)_(\d+))\s+((?:AI|AO|DI|DO)8\d{2})\b',
        re.IGNORECASE
    )

    # Concatenated 800-series card headers (e.g. AI8001 AI800)
    CARD_800_HEADER_REGEX = re.compile(
        r'^\s*((?:AI800|AO800|DI800|DO800)\d+)\s+(AI800|AO800|DI800|DO800)\b',
        re.IGNORECASE
    )

    CARD_HEADER_REGEX = re.compile(
        r'^\s*([A-Z]{2,12}\d+)\s+([A-Z]{2,12})\b',
        re.IGNORECASE
    )

    PARAM_REGEX = re.compile(
        r'^\s*:([A-Z0-9_]{1,30})\s*(.*)$',
        re.IGNORECASE
    )

    # Map hardware module types (AI810/DI820/…) onto exportable 800 families
    _HW_TYPE_TO_FAMILY = {
        "AI810": "AI800",
        "AO810": "AO800",
        "DI820": "DI800",
        "DO820": "DO800",
        "AI800": "AI800",
        "AO800": "AO800",
        "DI800": "DI800",
        "DO800": "DO800",
    }

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def is_card_header(self, line: str) -> Optional[Tuple[str, str]]:
        """
        Checks if line is a Card Definition header.
        Returns (card_name, family) where family is the exportable I/O family
        (AI800 for AI800_1 AI810 cards).
        """
        line_str = line.strip()

        match = self.CARD_800_UNDERSCORE_REGEX.match(line_str)
        if match:
            card_name = match.group(1).upper()
            hw_type = match.group(3).upper()
            family = self._HW_TYPE_TO_FAMILY.get(hw_type)
            if not family:
                # Derive from card prefix (AI800_1 → AI800)
                prefix = re.match(r'^(AI800|AO800|DI800|DO800)_', card_name)
                family = prefix.group(1) if prefix else None
            if family and card_name.startswith(family):
                return card_name, family
            return None

        match = self.CARD_800_HEADER_REGEX.match(line_str)
        if match:
            card_name = match.group(1).upper()
            family = match.group(2).upper()
            if card_name.startswith(family):
                return card_name, family
            return None

        match = self.CARD_HEADER_REGEX.match(line_str)
        if match:
            card_name = match.group(1).upper()
            family = match.group(2).upper()
            # Reject 800-series cards that fell into the generic pattern with a 2-letter family
            if re.match(r'^(?:AI800|AO800|DI800|DO800)(?:_?\d+)', card_name):
                return None
            if family in ("AI800", "AO800", "DI800", "DO800") or family in self._HW_TYPE_TO_FAMILY:
                return None
            if card_name.startswith(family) and family in card_name:
                return card_name, family
        return None

    def parse_card_records(
        self,
        card_name: str,
        family: str,
        records: List[LineRecord]
    ) -> CardNode:
        """Parses Card Node parameters from LineRecords."""
        parameters: Dict[str, Any] = {}
        page_num = records[0].page_number if records else 1

        for rec in records:
            match = self.PARAM_REGEX.match(rec.text)
            if match:
                key = match.group(1).upper()
                raw_val = match.group(2).strip()
                parameters[key] = self._clean_value(raw_val)

        self.logger.info(f"CardParser parsed Card Node '{card_name}' ({family}) with {len(parameters)} parameter(s).")
        return CardNode(family=family, card_name=card_name, page_number=page_num, parameters=parameters)

    def _clean_value(self, val_str: str) -> Any:
        if not val_str:
            return ""
        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            return val_str[1:-1].strip()
        if val_str.upper() in ('TRUE', 'YES', 'ON'):
            return True
        if val_str.upper() in ('FALSE', 'NO', 'OFF'):
            return False
        try:
            if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
                return int(val_str)
        except ValueError:
            pass
        try:
            return float(val_str)
        except ValueError:
            pass
        return val_str.strip('"\'')
