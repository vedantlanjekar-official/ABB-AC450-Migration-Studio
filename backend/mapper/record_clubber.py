"""
record_clubber.py — Club DB Element records by common Loop Tag.

Matching key = engineering NAME with the final suffix removed
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
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Any
from collections import defaultdict

from backend.models.db_element import DBElement
from backend.core.logging import get_logger


# Global family sections — processed in this order on the single worksheet
FAMILY_SECTIONS: List[Tuple[str, frozenset]] = [
    ("analog", frozenset({"AI", "AO"})),
    ("digital", frozenset({"DO", "DI"})),
    ("analog800", frozenset({"AI800", "AO800"})),
    ("digital800", frozenset({"DO800", "DI800"})),
]

# Within-club type order (lower = earlier)
ELEMENT_TYPE_ORDER: Dict[str, int] = {
    "AI": 10,
    "AO": 20,
    "DO": 30,
    "DI": 40,
    "AI800": 50,
    "AO800": 60,
    "DO800": 70,
    "DI800": 80,
}

# Valve / actuator suffix order within a digital Loop Tag club
VALVE_SUFFIX_ORDER: Dict[str, int] = {
    "SV1": 1,
    "GSO": 2,
    "GSC": 3,
}


def derive_loop_tag(name: str) -> str:
    """
    Derive common Loop Tag by stripping the final suffix after the last period.

    940FQ390.MV          → 940FQ390
    940XV101.RUN         → 940XV101
    940XV101.SV1         → 940XV101
    949DKA050.KEY:MAN    → 949DKA050  (colon attribute ignored)
    BOILER_PRESS_TR_01   → BOILER_PRESS_TR_01  (no suffix)
    """
    if not name:
        return ""
    tag = str(name).strip()
    if ":" in tag:
        tag = tag.split(":", 1)[0]
    tag = tag.rstrip(".:").strip()
    if "." in tag:
        return tag.rsplit(".", 1)[0]
    return tag


def derive_name_suffix(name: str) -> str:
    """Return the final suffix after the last period (uppercased), or empty string."""
    if not name:
        return ""
    tag = str(name).strip()
    if ":" in tag:
        tag = tag.split(":", 1)[0]
    tag = tag.rstrip(".:").strip()
    if "." in tag:
        return tag.rsplit(".", 1)[1].upper()
    return ""


class RecordClubber:
    """
    Clubs DB Element records that share a Loop Tag and emits them in
    family-section order for a single consolidated Valmet Excel worksheet.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def club_elements(self, elements: List[DBElement]) -> List[DBElement]:
        """
        Reorder elements into Loop Tag clubs within sequential family sections.

        Flow:
          1. AI–AO pairs (all Loop Tags)
          2. DO–DI pairs (all Loop Tags)
          3. AI800–AO800 pairs (all Loop Tags)
          4. DO800–DI800 pairs (all Loop Tags)

        Matching compares only the Loop Tag (NAME with suffix removed).
        Unpaired records are emitted without placeholders.
        """
        if not elements:
            return []

        by_family: Dict[str, List[DBElement]] = {name: [] for name, _ in FAMILY_SECTIONS}
        leftovers: List[DBElement] = []

        for elem in elements:
            etype = (elem.element_type or "").upper()
            placed = False
            for section_name, types in FAMILY_SECTIONS:
                if etype in types:
                    by_family[section_name].append(elem)
                    placed = True
                    break
            if not placed:
                leftovers.append(elem)

        clubbed: List[DBElement] = []
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

        self.logger.info(
            f"RecordClubber formed {club_count} Loop Tag club(s) "
            f"across {len(FAMILY_SECTIONS)} family section(s) "
            f"from {len(elements)} element(s)."
        )
        return clubbed

    def _club_section(
        self, elements: List[DBElement]
    ) -> Tuple[List[DBElement], int]:
        """Group one family section by Loop Tag and order within each club."""
        groups: Dict[str, List[DBElement]] = defaultdict(list)
        group_order: List[str] = []

        for elem in elements:
            name = elem.get_parameter("NAME")
            name_str = str(name).strip() if name not in (None, "") else ""
            loop_tag = derive_loop_tag(name_str) if name_str else ""
            key = loop_tag if loop_tag else f"__TAG__:{elem.tag}"
            if key not in groups:
                group_order.append(key)
            groups[key].append(elem)

        named_keys = sorted(k for k in group_order if not k.startswith("__TAG__:"))
        unnamed_keys = [k for k in group_order if k.startswith("__TAG__:")]
        ordered_keys = named_keys + unnamed_keys

        clubbed: List[DBElement] = []
        for key in ordered_keys:
            members_sorted = sorted(groups[key], key=self._within_group_sort_key)
            clubbed.extend(members_sorted)

        return clubbed, len(ordered_keys)

    def build_clubbed_overview(
        self,
        clubbed_elements: List[DBElement],
        mapped_sheets: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        Build a flat Clubbed_IO row list from club order
        (AI→AO section, then DO→DI, …) with Category + mapped columns.
        """
        row_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for etype, rows in mapped_sheets.items():
            for row in rows:
                row_index[(etype.upper(), str(row.get("Tag", "")))] = row

        overview: List[Dict[str, Any]] = []
        for elem in clubbed_elements:
            etype = (elem.element_type or "").upper()
            base = row_index.get((etype, elem.tag))
            if base is None:
                name = elem.get_parameter("NAME")
                name_str = str(name).strip() if name not in (None, "") else ""
                overview.append({
                    "Category": etype,
                    "Tag": elem.tag,
                    "Index": elem.element_index,
                    "NAME": name_str,
                    "Loop Tag": derive_loop_tag(name_str),
                })
                continue

            ordered: Dict[str, Any] = {"Category": etype}
            for col, val in base.items():
                if col == "Category":
                    continue
                ordered[col] = val
            if "Loop Tag" not in ordered:
                name = ordered.get("NAME", "")
                ordered["Loop Tag"] = derive_loop_tag(
                    str(name) if name not in (None, "") else ""
                )
            overview.append(ordered)

        self.logger.info(
            f"RecordClubber built Clubbed_IO overview with {len(overview)} row(s)."
        )
        return overview

    def club_mapped_sheets(
        self,
        mapped_sheets: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Club already-mapped row dicts and rebuild per-type lists,
        preserving club order within each type.
        """
        flat: List[Tuple[str, Dict[str, Any]]] = []
        for etype, rows in mapped_sheets.items():
            for row in rows:
                flat.append((etype.upper(), row))

        if not flat:
            return mapped_sheets

        pseudo: List[DBElement] = []
        row_by_id: Dict[int, Tuple[str, Dict[str, Any]]] = {}
        for idx, (etype, row) in enumerate(flat):
            name = row.get("NAME", "")
            elem = DBElement(
                tag=str(row.get("Tag", f"ROW{idx}")),
                element_type=etype,
                element_index=str(row.get("Index", "")),
                parameters={"NAME": name} if name not in (None, "") else {},
            )
            row_by_id[id(elem)] = (etype, row)
            pseudo.append(elem)

        clubbed_pseudo = self.club_elements(pseudo)

        rebuilt: Dict[str, List[Dict[str, Any]]] = {}
        for elem in clubbed_pseudo:
            etype, row = row_by_id[id(elem)]
            name = row.get("NAME", "")
            enriched = dict(row)
            if "Loop Tag" not in enriched:
                enriched["Loop Tag"] = derive_loop_tag(
                    str(name) if name not in (None, "") else ""
                )
            rebuilt.setdefault(etype, []).append(enriched)

        return rebuilt

    @staticmethod
    def _within_group_sort_key(elem: DBElement) -> Tuple[int, int, str, str]:
        etype = (elem.element_type or "").upper()
        name = elem.get_parameter("NAME")
        name_str = str(name).strip() if name not in (None, "") else ""
        suffix = derive_name_suffix(name_str)

        type_rank = ELEMENT_TYPE_ORDER.get(etype, 999)
        suffix_rank = VALVE_SUFFIX_ORDER.get(suffix, 100)
        return (type_rank, suffix_rank, name_str.upper(), elem.tag.upper())
