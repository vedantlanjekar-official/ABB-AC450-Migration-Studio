import re
from typing import Optional, Tuple, Dict, Any
from backend.core.logging import get_logger

class PCGrammarParser:
    """
    PC Element Structured Grammar Parser Module.
    Decomposes raw IO reference strings into Category, Card, Channel, Device Tag, and Loop Tag.
    Trims ONLY the final signal extension for Loop Tag extraction.
    """

    # Grammar regex matching: {FAMILY}{CARD}.{CHANNEL}/{DEVICE_TAG} or {FAMILY}_{CARD}.{CHANNEL}/{DEVICE_TAG}
    IO_REF_REGEX = re.compile(
        r'\b([A-Z]{2,12}\d{0,4})[_\s]?(\d+)[\.\:](\d+)\s*[\/\:]\s*([A-Z0-9_\-\.]+)\b',
        re.IGNORECASE
    )

    SIGNAL_EXTENSIONS = {
        "MV", "OUT", "RUN", "STOP", "OPEN", "CLOSE", "RDY", "STRT",
        "FAULT", "AUTO", "ON", "OFF", "SP", "PV", "IN", "PERM", "ALM",
        "TRIP", "ERR", "MANFD", "BYPASS", "RST", "CD1", "CA1", "CA11",
        "CA21", "CA12", "CA22", "SELECT", "HOLD", "LOAD", "POS", "MAN"
    }

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def parse_reference(self, raw_str: str) -> Optional[Dict[str, str]]:
        """
        Parses a raw IO reference string into structured fields.
        Returns Dict with keys: Category, Card, Channel, DeviceTag, LoopTag.
        """
        match = self.IO_REF_REGEX.search(raw_str.strip())
        if not match:
            return None

        category = match.group(1).upper()
        card_num = match.group(2)
        channel_num = match.group(3)
        device_tag = match.group(4).strip()

        loop_tag = self.extract_loop_tag(device_tag)

        return {
            "Category": category,
            "Card": card_num,
            "Channel": channel_num,
            "DeviceTag": device_tag,
            "LoopTag": loop_tag
        }

    def extract_loop_tag(self, device_tag: str) -> str:
        """
        Extracts Loop Tag from Device Tag by removing ONLY the last signal extension.
        e.g.,
          940LC391.MV    -> 940LC391
          945FC400.OUT   -> 945FC400
          940M03M1.RUN   -> 940M03M1
          946M22M2.STOP  -> 946M22M2
          S47LI395-2.MV  -> S47LI395-2
        """
        if "." not in device_tag:
            return device_tag

        parts = device_tag.rsplit(".", 1)
        prefix, ext = parts[0], parts[1]

        # Check if ext is a known signal suffix or short uppercase/digit extension
        if ext.upper() in self.SIGNAL_EXTENSIONS or (1 <= len(ext) <= 6 and ext.isalnum()):
            return prefix

        return device_tag
