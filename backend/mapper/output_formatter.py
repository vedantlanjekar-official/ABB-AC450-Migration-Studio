"""
output_formatter.py — Post-clubbing presentation layer for DB Element Excel export.

Does NOT change Loop Tag matching, clubbing, or extracted values.
Only reorders already-clubbed rows into the engineering sequence while
preserving the original Index column extracted from the PDF, then applies
Category → eight indicator columns after DESCR for final export.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from collections import defaultdict

from backend.core.logging import get_logger
from backend.mapper.record_clubber import derive_loop_tag, derive_name_suffix
from backend.mapper.category_mapper import apply_category_columns_after_description


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
    immediately before Excel generation, then expand Category into indicator columns.
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
        Then replace Category with AI/AO/DI/DO/AI800_/… indicator columns
        immediately after DESCR/Description.
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

        # Final export formatting: Category → eight indicator columns after DESCR
        export_rows = [
            apply_category_columns_after_description(row) for row in formatted
        ]
        # Canonicalize column order across all rows (Excel uses first-row keys)
        export_rows = self._canonicalize_export_columns(export_rows)

        self.logger.info(
            f"OutputFormatter arranged {len(export_rows)} row(s) into "
            f"{len(ordered_keys)} club group(s) across engineering sections "
            f"with category indicator columns after DESCR."
        )
        return export_rows

    @staticmethod
    def _canonicalize_export_columns(
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Ensure every row shares one column order with DESCR → indicators contiguous."""
        from backend.mapper.category_mapper import CATEGORY_INDICATOR_COLUMNS

        if not rows:
            return rows

        # Prefer order from the first row; union any extra keys at the end
        ordered_keys: List[str] = list(rows[0].keys())
        seen = set(ordered_keys)
        for row in rows[1:]:
            for key in row.keys():
                if key not in seen:
                    ordered_keys.append(key)
                    seen.add(key)

        # Enforce DESCR immediately followed by the eight indicators
        if "DESCR" in ordered_keys:
            without = [
                k for k in ordered_keys
                if k not in CATEGORY_INDICATOR_COLUMNS
            ]
            if "DESCR" in without:
                di = without.index("DESCR")
                ordered_keys = (
                    without[: di + 1]
                    + list(CATEGORY_INDICATOR_COLUMNS)
                    + without[di + 1:]
                )
            else:
                ordered_keys = without + list(CATEGORY_INDICATOR_COLUMNS)
        else:
            # Should not happen — still append indicators after identity cols
            without = [
                k for k in ordered_keys
                if k not in CATEGORY_INDICATOR_COLUMNS
            ]
            ordered_keys = without + ["DESCR"] + list(CATEGORY_INDICATOR_COLUMNS)

        return [
            {col: row.get(col, "") for col in ordered_keys}
            for row in rows
        ]

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
