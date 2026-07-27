import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from backend.parser.pdf_reader import LineRecord
from backend.models.db_element import DBElement
from backend.core.logging import get_logger

@dataclass
class ObjectNode:
    family: str
    card_name: str         # Parent Card (e.g. "AI1")
    identifier: str        # Full object tag (e.g. "AI1.4")
    index: str             # Object index (e.g. "1.4")
    page_number: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

class ObjectParser:
    """
    Stage 6 — Actual Engineering Object Node Parser Module.
    Parses Node Type 4 (Signal Objects e.g., AI1.4, AI2.14, AO3.8, AI8001.1).
    Objects are exportable engineering element nodes.
    """

    # 800-series families include digits in the type name — match before letter-only types
    OBJECT_800_HEADER_REGEX = re.compile(
        r'^\s*(AI800|AO800|DI800|DO800)\s*(\d+(?:\.\d+)*)\b',
        re.IGNORECASE
    )

    OBJECT_HEADER_REGEX = re.compile(
        r'^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\b',
        re.IGNORECASE
    )

    PARAM_REGEX = re.compile(
        r'^\s*:([A-Z0-9_]{1,30})\s*(.*)$',
        re.IGNORECASE
    )

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def is_object_header(self, line: str) -> Optional[Tuple[str, str, str]]:
        """
        Checks if line is an Object header (e.g. AI1.4 -> family="AI", index="1.4", identifier="AI1.4").
        Prefers AI800/AO800/DI800/DO800 over shorter AI/AO/DI/DO prefixes.
        """
        line_str = line.strip()
        match = self.OBJECT_800_HEADER_REGEX.match(line_str)
        if not match:
            match = self.OBJECT_HEADER_REGEX.match(line_str)
        if match:
            family = match.group(1).upper()
            index = match.group(2)
            identifier = f"{family}{index}"
            return family, index, identifier
        return None

    def parse_object_records(
        self,
        family: str,
        card_name: str,
        identifier: str,
        index: str,
        records: List[LineRecord]
    ) -> ObjectNode:
        """Parses Object Node parameters from LineRecords."""
        parameters: Dict[str, Any] = {}
        raw_lines: List[str] = []
        page_num = records[0].page_number if records else 1

        for rec in records:
            raw_lines.append(rec.text)
            match = self.PARAM_REGEX.match(rec.text)
            if match:
                key = match.group(1).upper()
                raw_val = match.group(2).strip()
                parameters[key] = self._clean_value(raw_val)

        return ObjectNode(
            family=family,
            card_name=card_name,
            identifier=identifier,
            index=index,
            page_number=page_num,
            parameters=parameters,
            raw_lines=raw_lines
        )

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
