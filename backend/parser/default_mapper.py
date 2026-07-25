import re
from typing import Dict
from backend.core.logging import get_logger

class DefaultMapper:
    """
    Resolves ABB AC450 default section names to target element types.
    
    Examples:
        DEFAULT AIS      -> AI
        DEFAULT AOS      -> AO
        DEFAULT DIS      -> DI
        DEFAULT DOS      -> DO
        DEFAULT PIDCON   -> PIDCON
        DEFAULT MANSTN   -> MANSTN
        DEFAULT MOTCON   -> MOTCON
        DEFAULT VALVECON -> VALVECON
        DEFAULT TEXT     -> TEXT
        DEFAULT TTDVAR   -> TTDVAR
        DEFAULT DIC      -> DIC
        DEFAULT DOC      -> DOC
        DEFAULT AIC      -> AIC
        DEFAULT AOC      -> AOC
    """

    DEFAULT_MAPPINGS: Dict[str, str] = {
        "AIS": "AI",
        "AOS": "AO",
        "DIS": "DI",
        "DOS": "DO",
        "DICS": "DIC",
        "DOCS": "DOC",
        "AICS": "AIC",
        "AOCS": "AOC",
        "PIDCON": "PIDCON",
        "PIDCONS": "PIDCON",
        "MANSTN": "MANSTN",
        "MANSTNS": "MANSTN",
        "MOTCON": "MOTCON",
        "MOTCONS": "MOTCON",
        "VALVECON": "VALVECON",
        "VALVECONS": "VALVECON",
        "RATIOSTN": "RATIOSTN",
        "RATIOSTNS": "RATIOSTN",
        "TEXT": "TEXT",
        "TEXTS": "TEXT",
        "TTDVAR": "TTDVAR",
        "TTDVARS": "TTDVAR",
        "DAT": "DAT",
        "DATS": "DAT",
        "DS": "DS",
        "DSS": "DS",
    }

    def __init__(self, custom_mappings: Dict[str, str] = None, job_id: str = None):
        self.logger = get_logger(job_id)
        self.mappings = dict(self.DEFAULT_MAPPINGS)
        if custom_mappings:
            for k, v in custom_mappings.items():
                self.mappings[k.upper()] = v.upper()

    def resolve_element_type(self, raw_default_name: str) -> str:
        """
        Normalizes a raw default section header string to its target element type.
        
        Args:
            raw_default_name: e.g. "DEFAULT AIS", "DEFAULT PIDCON", "DEFAULT CUSTOMS"
            
        Returns:
            Normalized uppercase element type string (e.g. "AI", "PIDCON")
        """
        cleaned = raw_default_name.strip().upper()
        # Remove DEFAULT or DEFAULTS prefix if present
        cleaned = re.sub(r'^\s*DEFAULT[S]?\s+', '', cleaned)

        # Check explicit mapping dictionary
        if cleaned in self.mappings:
            return self.mappings[cleaned]

        # Dynamic fallback heuristic for unknown future element default blocks:
        # e.g., if block name ends with 'S' and length > 3 (like CUSTOMS -> CUSTOM), strip trailing S
        if cleaned.endswith('S') and len(cleaned) > 2:
            candidate = cleaned[:-1]
            self.logger.info(f"Dynamic default name normalization: '{raw_default_name}' -> '{candidate}'")
            return candidate

        self.logger.info(f"Direct default name resolution: '{raw_default_name}' -> '{cleaned}'")
        return cleaned
