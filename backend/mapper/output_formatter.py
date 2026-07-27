"""
output_formatter.py — Post-clubbing presentation layer for DB Element Excel export.

Does NOT change Loop Tag matching, clubbing, or extracted values.
Only reorders already-clubbed rows into the engineering sequence and
renumbers the Index column to match the final row order.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from collections import defaultdict

from backend.core.logging import get_logger
from backend.mapper.record_clubber import derive_loop_tag, derive_name_suffix


# Presentation sections — emitted in this order on the single worksheet
OUTPUT_SECTIONS: List[Tuple[str, frozenset]] = [
    ("analog", frozenset({"AI", "AO"})),
    ("digital", frozenset({"DO", "DI"})),
    ("analog800", frozenset({"AI800", "AO800"})),
    ("digital800", frozenset({"DO800", "DI800"})),
]

# Within a Loop Tag club (paired records stay adjacent)
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
    Final formatting stage: sort clubbed rows into engineering sequence
    immediately before Excel generation.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def format_clubbed_rows(
        self, rows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reorder clubbed row dicts into:

          1. All AI → AO groups
          2. All DO → DI groups
          3. All AI800 → AO800 groups
          4. All DO800 → DI800 groups

        Paired records (same Loop Tag within a section) remain adjacent.
        Index is renumbered 1..N to match the final presentation order.
        """
        if not rows:
            return []

        section_rank = {
            name: idx for idx, (name, _) in enumerate(OUTPUT_SECTIONS)
        }
        type_to_section: Dict[str, str] = {}
        for name, types in OUTPUT_SECTIONS:
            for t in types:
                type_to_section[t] = name

        # Club key = (section, loop_tag) — preserves pair adjacency
        clubs: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        club_order: List[Tuple[str, str]] = []

        for row in rows:
            category = str(row.get("Category", "") or "").upper()
            name = row.get("NAME", "")
            name_str = str(name).strip() if name not in (None, "") else ""
            loop_tag = row.get("Loop Tag") or derive_loop_tag(name_str)
            loop_tag = str(loop_tag).strip() if loop_tag not in (None, "") else ""

            section = type_to_section.get(category, "__other__")
            key = (section, loop_tag if loop_tag else f"__ROW__:{row.get('Tag', '')}")
            if key not in clubs:
                club_order.append(key)
            clubs[key].append(dict(row))

        def club_sort_key(key: Tuple[str, str]) -> Tuple[int, str]:
            section, loop_tag = key
            return (section_rank.get(section, 999), loop_tag.upper())

        ordered_keys = sorted(club_order, key=club_sort_key)

        formatted: List[Dict[str, Any]] = []
        for key in ordered_keys:
            members = clubs[key]
            members_sorted = sorted(members, key=self._within_club_sort_key)
            formatted.extend(members_sorted)

        # Presentation Index = final row sequence (does not affect clubbing)
        for i, row in enumerate(formatted, start=1):
            row["Index"] = i

        self.logger.info(
            f"OutputFormatter arranged {len(formatted)} row(s) into "
            f"{len(ordered_keys)} club group(s) across engineering sections."
        )
        return formatted

    @staticmethod
    def _within_club_sort_key(row: Dict[str, Any]) -> Tuple[int, int, str, str]:
        category = str(row.get("Category", "") or "").upper()
        name = row.get("NAME", "")
        name_str = str(name).strip() if name not in (None, "") else ""
        suffix = derive_name_suffix(name_str)
        tag = str(row.get("Tag", "") or "")
        return (
            CATEGORY_ORDER.get(category, 999),
            VALVE_SUFFIX_ORDER.get(suffix, 100),
            name_str.upper(),
            tag.upper(),
        )
