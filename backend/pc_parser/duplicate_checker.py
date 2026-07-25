from typing import List, Tuple, Set
from backend.models.pc_element import PCElement
from backend.core.logging import get_logger

class PCDuplicateChecker:
    """
    PC Element Duplicate Checker & Sr No Assigner Module.
    Primary Key: (Category, Card Number, Channel Number, Device Tag).
    Deduplicates records and assigns auto-incrementing Sr No.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def deduplicate_and_number(self, elements: List[PCElement]) -> Tuple[List[PCElement], int]:
        """
        Deduplicates PCElements by Primary Key and assigns Sr No (1..N).
        Returns Tuple of (deduplicated_elements, duplicate_count).
        """
        seen_keys: Set[Tuple[str, str, str, str]] = set()
        deduped: List[PCElement] = []
        duplicate_count = 0

        for elem in elements:
            pkey = (
                elem.category.upper(),
                elem.card_number,
                elem.channel_number,
                elem.device_tag.upper()
            )

            if pkey in seen_keys:
                duplicate_count += 1
                self.logger.debug(f"PCDuplicateChecker ignored duplicate PC Element: {pkey}")
            else:
                seen_keys.add(pkey)
                deduped.append(elem)

        # Assign 1-based Sr No
        for idx, elem in enumerate(deduped, start=1):
            elem.sr_no = idx

        self.logger.info(f"PCDuplicateChecker deduplicated {len(elements)} element(s) into {len(deduped)} unique record(s) ({duplicate_count} duplicate(s) removed).")
        return deduped, duplicate_count
