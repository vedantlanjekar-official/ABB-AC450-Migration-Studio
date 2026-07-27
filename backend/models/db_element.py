from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class DBElement:
    """
    Internal model representing a parsed ABB AC450 Database Element object.
    
    Attributes:
        tag: Full element tag/header (e.g., 'AI1.4', 'AO2.6', 'DI8001.1')
        element_type: Extracted type prefix (e.g., 'AI', 'AO', 'DI', 'DO', 'AI800')
        element_index: Object index/number (e.g., '1.4', '2.6', '3')
        parameters: Dynamic map of colon-prefixed parameter keys and their extracted values.
                    Key format: 'NAME', 'UNIT', 'DESCR', 'RANGEMAX', etc. (without colon)
        raw_text: Raw text lines for debugging / fallback analysis
        page_number: Source page number in PDF
        file_name: Source PDF file name
    """
    tag: str
    element_type: str
    element_index: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    page_number: int = 1
    file_name: str = ""

    def get_parameter(self, key: str, default: Any = None) -> Any:
        cleaned_key = key.lstrip(':').upper()
        return self.parameters.get(cleaned_key, default)
