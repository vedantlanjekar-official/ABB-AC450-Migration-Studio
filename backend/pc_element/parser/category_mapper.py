"""
category_mapper.py — PC Element re-export of shared Category indicator mapping.

Implementation lives in backend.mapper.category_mapper so DB and PC stay in sync.
"""

from backend.mapper.category_mapper import (  # noqa: F401
    CATEGORY_INDICATOR_COLUMNS,
    apply_category_columns,
    build_category_indicator_values,
    category_to_indicator_column,
    normalize_category_key,
)
