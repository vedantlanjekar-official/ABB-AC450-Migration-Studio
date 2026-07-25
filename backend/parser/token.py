from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Any

class TokenType(Enum):
    DEFAULT_START = auto()   # e.g., DEFAULT AIS, DEFAULT AI, DEFAULT AOS
    DEFAULT_END = auto()     # e.g., *** END OF DEFAULTS ***
    OBJECT_START = auto()    # e.g., AI1.4, AI1.1, AO2.1, PIDCON1, MOTCON1
    PARAMETER = auto()       # e.g., :NAME 940PI726.MV, :UNIT bar, :DESCR
    TEXT = auto()            # Unrecognized line text

@dataclass
class Token:
    token_type: TokenType
    raw_line: str
    page_number: int
    name: Optional[str] = None       # Default block name or parameter key
    value: Optional[Any] = None      # Parameter value (can be empty string "")
    family: Optional[str] = None     # Object family (e.g. "AI", "AO", "PIDCON")
    identifier: Optional[str] = None # Full object tag (e.g. "AI1.4")
    index: Optional[str] = None      # Object index (e.g. "1.4")
