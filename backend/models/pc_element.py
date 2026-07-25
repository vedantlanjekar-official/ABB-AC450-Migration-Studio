from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class PCElement:
    """
    Structured Engineering Object for an ABB AC450 PC Element IO Reference.
    """
    category: str           # e.g., AI, AO, DI, DO, AI800, AO800, DI800, DO800
    card_number: str        # e.g., "1", "3", "800_1"
    channel_number: str     # e.g., "1", "14", "6"
    loop_tag: str           # e.g., "940LC391", "945FC400"
    device_tag: str         # e.g., "940LC391.MV", "945FC400.OUT"
    description: str = ""   # e.g., "PURE WATER TANK LEVEL"
    sr_no: int = 0
    page_number: int = 1
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Sr No": self.sr_no,
            "Loop Tag": self.loop_tag,
            "Description": self.description,
            "Device Tag": self.device_tag,
            "Category": self.category,
            "Card Number": self.card_number,
            "Channel Number": self.channel_number,
        }
