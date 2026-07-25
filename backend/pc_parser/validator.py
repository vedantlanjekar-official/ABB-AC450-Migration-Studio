from typing import List, Dict, Tuple
from backend.models.pc_element import PCElement
from backend.core.logging import get_logger

class PCElementValidator:
    """
    PC Element Validation Module.
    Validates that every PCElement contains Category, Card Number, Channel Number, Device Tag, and Loop Tag.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def validate_records(self, records: List[Dict[str, str]]) -> Tuple[List[PCElement], int, List[str]]:
        """
        Validates raw dict records and instantiates PCElement objects.
        Returns Tuple of (valid_elements, invalid_count, list_of_warnings).
        """
        valid_elements: List[PCElement] = []
        invalid_count = 0
        warnings: List[str] = []

        for r in records:
            category = r.get("Category", "").strip()
            card = r.get("Card", "").strip()
            channel = r.get("Channel", "").strip()
            device_tag = r.get("DeviceTag", "").strip()
            loop_tag = r.get("LoopTag", "").strip()
            description = r.get("Description", "").strip()
            page_num = int(r.get("PageNumber", 1))
            raw_text = r.get("RawText", "")

            if not (category and card and channel and device_tag and loop_tag):
                invalid_count += 1
                warnings.append(f"Invalid PC Element reference on page {page_num}: missing essential fields ({device_tag})")
                continue

            elem = PCElement(
                category=category,
                card_number=card,
                channel_number=channel,
                device_tag=device_tag,
                loop_tag=loop_tag,
                description=description,
                page_number=page_num,
                raw_text=raw_text
            )
            valid_elements.append(elem)

        self.logger.info(f"PCElementValidator validated {len(valid_elements)} element(s) cleanly ({invalid_count} invalid).")
        return valid_elements, invalid_count, warnings
