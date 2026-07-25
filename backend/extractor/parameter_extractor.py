import re
from typing import Dict, Any, List
from backend.core.logging import get_logger

class ParameterExtractor:
    """
    Extracts key-value parameter pairs from ABB AC450 DB element block text.
    Handles colon-prefixed parameters (:KEY VALUE).
    Fully data-driven and dynamic - never hardcodes parameter names.
    """
    
    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def extract_parameters(self, block_text: str) -> Dict[str, Any]:
        """
        Parses colon-prefixed parameter key-value pairs from block text.
        
        Args:
            block_text: Raw string buffer containing lines for an element block.
            
        Returns:
            Dict[str, Any] mapping uppercase parameter names to parsed values.
        """
        parameters: Dict[str, Any] = {}
        if not block_text or not block_text.strip():
            return parameters

        # Find all colon parameters in the block text
        # Pattern looks for :KEY followed by text up until next :KEY or end of line/block
        tokens = re.finditer(r':([A-Z0-9_]{1,30})\s*(.*?)(?=\s+:[A-Z0-9_]{1,30}|\r?\n|\Z)', block_text, re.DOTALL | re.IGNORECASE)
        
        for match in tokens:
            raw_key = match.group(1).strip().upper()
            raw_val = match.group(2).strip()
            
            # Clean and coerce parameter value
            parsed_val = self._clean_value(raw_val)
            parameters[raw_key] = parsed_val

        # Fallback regex scan for multiline or line-by-line colon parameters if needed
        if not parameters:
            for line in block_text.splitlines():
                line_str = line.strip()
                if line_str.startswith(':'):
                    parts = line_str.split(maxsplit=1)
                    key = parts[0].lstrip(':').upper()
                    val = parts[1].strip() if len(parts) > 1 else ""
                    parameters[key] = self._clean_value(val)

        return parameters

    def _clean_value(self, val_str: str) -> Any:
        if not val_str:
            return ""

        # Remove matching quotes if enclosed
        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            return val_str[1:-1].strip()

        # Coerce boolean
        if val_str.upper() in ('TRUE', 'YES', 'ON'):
            return True
        if val_str.upper() in ('FALSE', 'NO', 'OFF'):
            return False

        # Coerce integer
        try:
            if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
                return int(val_str)
        except ValueError:
            pass

        # Coerce float
        try:
            return float(val_str)
        except ValueError:
            pass

        # Clean trailing noise/quotes
        cleaned = val_str.strip('"\'')
        return cleaned
