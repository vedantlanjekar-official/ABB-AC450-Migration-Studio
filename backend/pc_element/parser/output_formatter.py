"""
output_formatter.py — Post-clubbing presentation layer for PC Element Excel export.

Does NOT change Loop Tag matching, clubbing, or extracted values.
Only reorders already-clubbed EngineeringIO records into the engineering
sequence immediately before Excel generation.
"""

from __future__ import annotations

from typing import List, Tuple, Dict
from collections import defaultdict
import logging

from backend.pc_element.parser.validator import EngineeringIO
from backend.mapper.record_clubber import derive_loop_tag, derive_name_suffix


logger = logging.getLogger("pc_element_parser")

# Presentation sections — emitted in this order on the single worksheet
OUTPUT_SECTIONS: List[Tuple[str, frozenset]] = [
    ("analog", frozenset({"AI", "AO"})),
    ("digital", frozenset({"DO", "DI"})),
    ("analog800", frozenset({"AI800", "AO800"})),
    ("digital800", frozenset({"DO800", "DI800"})),
]

CATEGORY_ORDER: Dict[str, int] = {
    "AI": 10,
    "AO": 20,
    "DO": 30,
    "DI": 40,
    "AI800": 50,
    "AO800": 60,
    "DO800": 70,
    "DI800": 80,
}

VALVE_SUFFIX_ORDER: Dict[str, int] = {
    "SV1": 1,
    "GSO": 2,
    "GSC": 3,
}


class OutputFormatter:
    """
    Final formatting stage: sort clubbed PC Element records into engineering
    sequence immediately before Excel generation.
    """

    def __init__(self, job_id: str = None):
        self.job_id = job_id or "pc_formatter"

    def format_clubbed_elements(
        self, elements: List[EngineeringIO]
    ) -> List[EngineeringIO]:
        """
        Reorder clubbed EngineeringIO records into:

          1. All AI → AO groups
          2. All DO → DI groups
          3. All AI800 → AO800 groups
          4. All DO800 → DI800 groups

        Paired records (same Loop Tag within a section) remain adjacent.
        Extracted engineering data is preserved exactly — only row order changes.
        """
        if not elements:
            return []

        section_rank = {
            name: idx for idx, (name, _) in enumerate(OUTPUT_SECTIONS)
        }
        type_to_section: Dict[str, str] = {}
        for name, types in OUTPUT_SECTIONS:
            for t in types:
                type_to_section[t] = name

        clubs: Dict[Tuple[str, str], List[EngineeringIO]] = defaultdict(list)
        club_order: List[Tuple[str, str]] = []

        for elem in elements:
            category = (elem.category or "").upper()
            loop_tag = (elem.loop_tag or "").strip()
            if not loop_tag:
                loop_tag = derive_loop_tag(elem.device_tag or "")

            section = type_to_section.get(category, "__other__")
            key = (
                section,
                loop_tag if loop_tag else f"__ROW__:{elem.device_tag}",
            )
            if key not in clubs:
                club_order.append(key)
            clubs[key].append(elem)

        def club_sort_key(key: Tuple[str, str]) -> Tuple[int, str]:
            section, loop_tag = key
            return (section_rank.get(section, 999), loop_tag.upper())

        ordered_keys = sorted(club_order, key=club_sort_key)

        formatted: List[EngineeringIO] = []
        for key in ordered_keys:
            members = clubs[key]
            members_sorted = sorted(members, key=self._within_club_sort_key)
            formatted.extend(members_sorted)

        logger.info(
            f"[{self.job_id}] OutputFormatter arranged {len(formatted)} row(s) into "
            f"{len(ordered_keys)} club group(s) across engineering sections."
        )
        return formatted

    @staticmethod
    def _within_club_sort_key(elem: EngineeringIO) -> Tuple[int, int, str, str]:
        category = (elem.category or "").upper()
        device = (elem.device_tag or "").strip()
        suffix = derive_name_suffix(device)
        return (
            CATEGORY_ORDER.get(category, 999),
            VALVE_SUFFIX_ORDER.get(suffix, 100),
            device.upper(),
            (elem.source_reference or "").upper(),
        )
