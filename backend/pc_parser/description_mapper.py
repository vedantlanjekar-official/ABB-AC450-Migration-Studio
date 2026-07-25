import re
from typing import List, Tuple, Dict, Optional
from backend.pc_parser.pdf_reader import PCLineRecord
from backend.pc_parser.grammar_parser import PCGrammarParser
from backend.core.logging import get_logger

class PCDescriptionMapper:
    """
    PC Element Description Mapper Module.
    Inspects surrounding engineering text lines to find the nearest engineering description
    for each IO reference.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)
        self.grammar_parser = PCGrammarParser(job_id)

    def attach_descriptions(
        self,
        detected_refs: List[Tuple[Dict[str, str], PCLineRecord]],
        all_cleaned_records: List[PCLineRecord]
    ) -> List[Dict[str, str]]:
        """
        Attaches nearest engineering description to each detected IO reference.
        """
        # Map record id / line index for fast neighborhood lookup
        record_map: Dict[Tuple[int, int], int] = {
            (r.page_number, r.line_number): idx for idx, r in enumerate(all_cleaned_records)
        }

        results: List[Dict[str, str]] = []

        for ref_dict, ref_rec in detected_refs:
            ref_data = dict(ref_dict)
            ref_data["PageNumber"] = str(ref_rec.page_number)
            ref_data["RawText"] = ref_rec.text

            # Look up index of this line in all_cleaned_records
            key = (ref_rec.page_number, ref_rec.line_number)
            idx = record_map.get(key)

            desc = ""
            if idx is not None:
                desc = self._find_nearest_description(idx, all_cleaned_records)

            ref_data["Description"] = desc
            results.append(ref_data)

        self.logger.info(f"PCDescriptionMapper attached descriptions to {len(results)} IO reference(s).")
        return results

    def _find_nearest_description(
        self,
        ref_idx: int,
        records: List[PCLineRecord],
        window_size: int = 4
    ) -> str:
        """
        Searches sliding window around ref_idx for an engineering description line.
        """
        total = len(records)

        # 1. Search lines below (forward window)
        for offset in range(1, window_size + 1):
            target_idx = ref_idx + offset
            if target_idx < total:
                text = records[target_idx].text.strip()
                if self._is_valid_description_candidate(text):
                    return text

        # 2. Search lines above (backward window)
        for offset in range(1, window_size + 1):
            target_idx = ref_idx - offset
            if target_idx >= 0:
                text = records[target_idx].text.strip()
                if self._is_valid_description_candidate(text):
                    return text

        return ""

    def _is_valid_description_candidate(self, text: str) -> bool:
        """Checks if text string is a valid engineering description line."""
        if not text:
            return False
        # Cannot be another IO reference (e.g. AI1.1/940LC391.MV)
        if self.grammar_parser.parse_reference(text):
            return False
        # Cannot start with colon parameter declaration (e.g. :NAME)
        if text.startswith(":"):
            return False
        # Cannot be pure numbers or card tag alone (e.g. AI1.2, AI1 AI)
        if re.match(r'^\s*[A-Z]{2,12}\d+(?:\.\d+)*\s*$', text, re.IGNORECASE):
            return False
        # Must contain at least one alpha character
        if not any(c.isalpha() for c in text):
            return False
        return True
