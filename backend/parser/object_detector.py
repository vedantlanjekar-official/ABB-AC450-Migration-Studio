import re
from typing import Optional, Tuple

class ObjectDetector:
    """
    Identifies the start and end boundaries of actual ABB DB element objects
    (e.g., AI1.1, AI1.2, AO2.1, PIDCON1, MOTCON1, VALVECON1, DS1, DAT1, TEXT1).
    """

    OBJECT_HEADER_REGEX = re.compile(
        r'^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\b'
    )

    # Exclude default section titles
    DEFAULT_PREFIX_REGEX = re.compile(
        r'^\s*DEFAULT\b',
        re.IGNORECASE
    )

    def is_object_header(self, line: str) -> Optional[Tuple[str, str, str]]:
        """
        Checks if line starts an element object header.
        
        Args:
            line: Raw line text string
            
        Returns:
            Tuple of (element_type, index_str, full_tag) or None
        """
        line_str = line.strip()
        if not line_str or self.DEFAULT_PREFIX_REGEX.match(line_str):
            return None

        match = self.OBJECT_HEADER_REGEX.match(line_str)
        if match:
            elem_type = match.group(1).upper()
            elem_index = match.group(2)
            full_tag = f"{elem_type}{elem_index}"
            return elem_type, elem_index, full_tag

        return None
