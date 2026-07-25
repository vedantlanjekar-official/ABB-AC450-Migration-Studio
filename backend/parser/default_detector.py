import re
from typing import Optional

class DefaultDetector:
    """
    Locates DEFAULT block headers and *** END OF DEFAULTS *** section markers in line text streams.
    Handles all formatting variations in ABB AC450 PDFs.
    """

    # Matches: DEFAULT AI, DEFAULT AIS, DEFAULT: AIS, DEFAULT  AIS, DEFAULTS AIS
    DEFAULT_HEADER_REGEX = re.compile(
        r'^\s*DEFAULT[S]?[:\s\-]+([A-Z0-9_]+)\b',
        re.IGNORECASE
    )

    # Matches: *** END OF DEFAULTS ***, END OF DEFAULTS, *** END OF DEFAULT ***
    END_DEFAULTS_REGEX = re.compile(
        r'^\s*\*{0,10}\s*END\s+OF\s+DEFAULTS?\s*\*{0,10}\s*$',
        re.IGNORECASE
    )

    def is_default_header(self, line: str) -> Optional[str]:
        """
        Checks if line starts a DEFAULT block.
        Returns raw block name (e.g. "AI", "AIS", "AO", "AOS", "PIDCON") or None.
        """
        line_str = line.strip()
        match = self.DEFAULT_HEADER_REGEX.match(line_str)
        if match:
            return match.group(1).upper()
        
        # Fallback check for DEFAULT <NAME> anywhere on line
        if line_str.upper().startswith("DEFAULT"):
            parts = line_str.split()
            if len(parts) >= 2:
                raw_name = parts[1].strip(":-_").upper()
                if raw_name and raw_name not in ("OF", "DEFAULTS", "BLOCK", "SECTION"):
                    return raw_name
        return None

    def is_end_of_defaults(self, line: str) -> bool:
        """
        Checks if line matches *** END OF DEFAULTS *** marker.
        """
        line_str = line.strip()
        if self.END_DEFAULTS_REGEX.match(line_str):
            return True
        if "END OF DEFAULT" in line_str.upper():
            return True
        return False
