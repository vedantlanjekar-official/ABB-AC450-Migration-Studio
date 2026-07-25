import re
from typing import Optional, Tuple
from enum import Enum, auto

class LineType(Enum):
    DEFAULT_HEADER = auto()
    OBJECT_HEADER = auto()
    PARAM_COLON = auto()
    OTHER = auto()

class SectionDetector:
    """
    Detects section boundaries and classifies lines for state machine transitions.
    """

    DEFAULT_REGEX = re.compile(
        r'^\s*DEFAULT[S]?\s+([A-Z0-9_]+)\b',
        re.IGNORECASE
    )

    OBJECT_REGEX = re.compile(
        r'^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\b'
    )

    PARAM_REGEX = re.compile(
        r'^\s*:([A-Z0-9_]{1,30})\b'
    )

    def classify_line(self, line: str) -> Tuple[LineType, Optional[str], Optional[Tuple[str, str]]]:
        """
        Classifies line and extracts header metadata.
        
        Returns:
            Tuple of (LineType, default_raw_name_if_default, (elem_type, index)_if_object)
        """
        line_str = line.strip()
        if not line_str:
            return LineType.OTHER, None, None

        # Check DEFAULT header
        match_def = self.DEFAULT_REGEX.match(line_str)
        if match_def:
            return LineType.DEFAULT_HEADER, line_str, None

        # Check OBJECT header
        match_obj = self.OBJECT_REGEX.match(line_str)
        if match_obj:
            elem_type = match_obj.group(1).upper()
            elem_index = match_obj.group(2)
            return LineType.OBJECT_HEADER, None, (elem_type, elem_index)

        # Check PARAM colon
        if self.PARAM_REGEX.match(line_str):
            return LineType.PARAM_COLON, None, None

        return LineType.OTHER, None, None
