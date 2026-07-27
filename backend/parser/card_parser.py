import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from backend.parser.pdf_reader import LineRecord
from backend.core.logging import get_logger

@dataclass
class CardNode:
    family: str
    card_name: str       # e.g. "AI1", "AI2", "AO1", "DI1"
    page_number: int
    parameters: Dict[str, Any] = field(default_factory=dict)

class CardParser:
    """
    Stage 5 — Card Definition Node Parser Module.
    Parses Node Type 3 (Card Definitions e.g., AI1 AI, AI2 AI, AO1 AO).
    Card Nodes are AST parents holding Card Parameters (:ADDR 32, :CONV_PAR 4..20mA).
    CARD NODES ARE NOT OBJECTS AND ARE NEVER EXPORTED TO EXCEL.
    """

    # 800-series card headers (e.g. AI8001 AI800) — match before letter-only families
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

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def is_card_header(self, line: str) -> Optional[Tuple[str, str]]:
        """
        Checks if line is a Card Definition header (e.g., AI1 AI -> card_name="AI1", family="AI").
        """
        line_str = line.strip()
        match = self.CARD_800_HEADER_REGEX.match(line_str)
        if not match:
            match = self.CARD_HEADER_REGEX.match(line_str)
        if match:
            card_name = match.group(1).upper()
            family = match.group(2).upper()
            if family in card_name:
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
