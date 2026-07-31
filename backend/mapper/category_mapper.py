"""
category_mapper.py — Final-export Category → indicator-column transform.

Shared by DB Element and PC Element Excel export. Does NOT change extraction,
clubbing, or row order — only reshapes Category into eight indicator columns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

# Excel column headers (800-series keep the trailing underscore per Valmet layout)
CATEGORY_INDICATOR_COLUMNS: List[str] = [
    "AI",
    "AO",
    "DI",
    "DO",
    "AI800_",
    "AO800_",
    "DI800_",
    "DO800_",
]

# Map internal Category codes (and underscore aliases) → indicator column name
_CATEGORY_TO_COLUMN: Dict[str, str] = {
    "AI": "AI",
    "AO": "AO",
    "DI": "DI",
    "DO": "DO",
    "AI800": "AI800_",
    "AO800": "AO800_",
    "DI800": "DI800_",
    "DO800": "DO800_",
    "AI800_": "AI800_",
    "AO800_": "AO800_",
    "DI800_": "DI800_",
    "DO800_": "DO800_",
}

_DESCRIPTION_KEYS = ("DESCR", "Description")


def normalize_category_key(category: Optional[str]) -> str:
    """Normalize a Category / io_family value for column lookup."""
    if not category:
        return ""
    return str(category).strip().upper()


def category_to_indicator_column(category: Optional[str]) -> Optional[str]:
    """Return the indicator column name for a Category value, or None if unknown."""
    return _CATEGORY_TO_COLUMN.get(normalize_category_key(category))


def build_category_indicator_values(category: Optional[str]) -> Dict[str, Any]:
    """
    Build the eight category indicator cells for one record.

    The matching column is set to 1; all others remain blank (project standard).
    """
    values: Dict[str, Any] = {col: "" for col in CATEGORY_INDICATOR_COLUMNS}
    target = category_to_indicator_column(category)
    if target:
        values[target] = 1
    return values


def apply_category_columns(
    row: Mapping[str, Any],
    *,
    category_key: str = "Category",
) -> Dict[str, Any]:
    """
    Return a row dict with Category replaced by the eight indicator columns
    in-place (where Category previously appeared).

    Used by PC Element export.
    """
    indicators = build_category_indicator_values(row.get(category_key))
    out: Dict[str, Any] = {}
    inserted = False
    for key, value in row.items():
        if key == category_key:
            out.update(indicators)
            inserted = True
            continue
        if key in CATEGORY_INDICATOR_COLUMNS:
            continue
        out[key] = value
    if not inserted:
        out.update(indicators)
    return out


def apply_category_columns_after_description(
    row: Mapping[str, Any],
    *,
    category_key: str = "Category",
    description_keys: Sequence[str] = _DESCRIPTION_KEYS,
) -> Dict[str, Any]:
    """
    Return a row dict with eight indicator columns inserted immediately after
    the DESCR column (mandatory placement). The original Category column is removed.

    Always emits a DESCR column (blank when the source record has no description).
    Any alias such as \"Description\" is normalized to DESCR.
    """
    indicators = build_category_indicator_values(row.get(category_key))
    desc_keys = set(description_keys)

    if "DESCR" in row and row.get("DESCR") is not None:
        desc_val: Any = row.get("DESCR")
    elif "Description" in row and row.get("Description") is not None:
        desc_val = row.get("Description")
    else:
        desc_val = ""

    before: List[tuple[str, Any]] = []
    after: List[tuple[str, Any]] = []
    seen_descr = False

    for key, value in row.items():
        if key == category_key or key in CATEGORY_INDICATOR_COLUMNS:
            continue
        if key in desc_keys:
            seen_descr = True
            continue
        if not seen_descr:
            before.append((key, value))
        else:
            after.append((key, value))

    # If DESCR was absent, keep identity columns in `before` and insert DESCR
    # after Loop Tag (preferred) or NAME so remaining params stay in `after`.
    if not seen_descr and before:
        split_at = None
        for idx, (key, _) in enumerate(before):
            if key == "Loop Tag":
                split_at = idx
                break
        if split_at is None:
            for idx, (key, _) in enumerate(before):
                if key == "NAME":
                    split_at = idx
                    break
        if split_at is not None:
            after = before[split_at + 1:] + after
            before = before[: split_at + 1]

    out: Dict[str, Any] = {}
    for key, value in before:
        out[key] = value
    out["DESCR"] = desc_val if desc_val is not None else ""
    out.update(indicators)
    for key, value in after:
        out[key] = value
    return out
