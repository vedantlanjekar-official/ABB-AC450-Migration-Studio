import re
from typing import Dict, Any, List
from backend.parser.pdf_reader import LineRecord
from backend.core.logging import get_logger

class DefaultParser:
    """
    Stage 4 — Default Definitions Parser Module.
    Parses Node Type 1 (Hardware Defaults) and Node Type 2 (Signal Defaults).
    Preserves empty parameters (:DESCR -> DESCR = "").
    """

    PARAM_REGEX = re.compile(
        r'^\s*:([A-Z0-9_]{1,30})\s*(.*)$',
        re.IGNORECASE
    )

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def parse_default_lines(self, block_name: str, records: List[LineRecord]) -> Dict[str, Any]:
        """Parses parameter key-value pairs from DEFAULT block lines."""
        parameters: Dict[str, Any] = {}

        for rec in records:
            match = self.PARAM_REGEX.match(rec.text)
            if match:
                key = match.group(1).upper()
                raw_val = match.group(2).strip()
                cleaned_val = self._clean_value(raw_val)
                parameters[key] = cleaned_val

        self.logger.info(f"DefaultParser parsed {len(parameters)} default parameter(s) for '{block_name}'")
        return parameters

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
