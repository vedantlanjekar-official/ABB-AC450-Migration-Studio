"""
record_clubber.py — Club PC Element I/O records by common Loop Tag.

Mirrors the DB Element RecordClubber so both converters share the same
engineering presentation rules.

Matching key = device tag with the final suffix removed
  e.g. 940FQ390.MV / 940FQ390.OUT → Loop Tag 940FQ390

Global sheet order (family sections, not mixed by Loop Tag):
  1. All AI–AO clubs
  2. All DO–DI clubs
  3. All AI800–AO800 clubs
  4. All DO800–DI800 clubs

Within each Loop Tag club:
  AI → AO | DO → DI | AI800 → AO800 | DO800 → DI800
  Valve suffixes (digital): .SV1 → .GSO → .GSC

Unpaired records are kept; no empty placeholders are created.
Only the eight supported categories are clubbed (others ignored as leftovers).
"""

from __future__ import annotations

from typing import List, Tuple, Dict
from collections import defaultdict
import logging

from backend.pc_element.parser.validator import EngineeringIO
from backend.mapper.record_clubber import derive_loop_tag, derive_name_suffix


logger = logging.getLogger("pc_element_parser")

# Global family sections — processed in this order on the single worksheet
FAMILY_SECTIONS: List[Tuple[str, frozenset]] = [
    ("analog", frozenset({"AI", "AO"})),
    ("digital", frozenset({"DO", "DI"})),
    ("analog800", frozenset({"AI800", "AO800"})),
    ("digital800", frozenset({"DO800", "DI800"})),
]

# Within-club type order (lower = earlier) — uses Category (no trailing underscore)
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


class RecordClubber:
    """
    Clubs PC Element EngineeringIO records that share a Loop Tag and emits
    them in family-section order for a single consolidated I/O worksheet.
    """

    def __init__(self, job_id: str = None):
        self.job_id = job_id or "pc_clubber"

    def club_elements(self, elements: List[EngineeringIO]) -> List[EngineeringIO]:
        """
        Reorder elements into Loop Tag clubs within sequential family sections.

        Flow:
          1. AI–AO pairs (all Loop Tags)
          2. DO–DI pairs (all Loop Tags)
          3. AI800–AO800 pairs (all Loop Tags)
          4. DO800–DI800 pairs (all Loop Tags)

        Matching compares only the Loop Tag (device_tag with suffix removed).
        Unpaired records are emitted without placeholders.
        """
        if not elements:
            return []

        by_family: Dict[str, List[EngineeringIO]] = {
            name: [] for name, _ in FAMILY_SECTIONS
        }
        leftovers: List[EngineeringIO] = []

        for elem in elements:
            category = (elem.category or "").upper()
            placed = False
            for section_name, types in FAMILY_SECTIONS:
                if category in types:
                    by_family[section_name].append(elem)
                    placed = True
                    break
            if not placed:
                leftovers.append(elem)

        clubbed: List[EngineeringIO] = []
        club_count = 0

        for section_name, _ in FAMILY_SECTIONS:
            section_elems = by_family[section_name]
            if not section_elems:
                continue
            section_clubbed, n_clubs = self._club_section(section_elems)
            clubbed.extend(section_clubbed)
            club_count += n_clubs

        if leftovers:
            leftover_clubbed, n_clubs = self._club_section(leftovers)
            clubbed.extend(leftover_clubbed)
            club_count += n_clubs

        logger.info(
            f"[{self.job_id}] RecordClubber formed {club_count} Loop Tag club(s) "
            f"across {len(FAMILY_SECTIONS)} family section(s) "
            f"from {len(elements)} element(s)."
        )
        return clubbed

    def _club_section(
        self, elements: List[EngineeringIO]
    ) -> Tuple[List[EngineeringIO], int]:
        """Group one family section by Loop Tag and order within each club."""
        groups: Dict[str, List[EngineeringIO]] = defaultdict(list)
        group_order: List[str] = []

        for elem in elements:
            loop_tag = self._resolve_loop_tag(elem)
            key = loop_tag if loop_tag else f"__TAG__:{elem.device_tag}"
            if key not in groups:
                group_order.append(key)
            groups[key].append(elem)

        named_keys = sorted(k for k in group_order if not k.startswith("__TAG__:"))
        unnamed_keys = [k for k in group_order if k.startswith("__TAG__:")]
        ordered_keys = named_keys + unnamed_keys

        clubbed: List[EngineeringIO] = []
        for key in ordered_keys:
            members_sorted = sorted(groups[key], key=self._within_group_sort_key)
            clubbed.extend(members_sorted)

        return clubbed, len(ordered_keys)

    @staticmethod
    def _resolve_loop_tag(elem: EngineeringIO) -> str:
        """Always derive from device_tag for DB clubbing parity."""
        from backend.mapper.record_clubber import derive_loop_tag
        return derive_loop_tag(elem.device_tag or "") or (elem.loop_tag or "").strip()

    @staticmethod
    def _within_group_sort_key(elem: EngineeringIO) -> Tuple[int, int, str, str]:
        category = (elem.category or "").upper()
        device = (elem.device_tag or "").strip()
        suffix = derive_name_suffix(device)

        type_rank = CATEGORY_ORDER.get(category, 999)
        suffix_rank = VALVE_SUFFIX_ORDER.get(suffix, 100)
        return (
            type_rank,
            suffix_rank,
            device.upper(),
            (elem.source_reference or "").upper(),
        )
