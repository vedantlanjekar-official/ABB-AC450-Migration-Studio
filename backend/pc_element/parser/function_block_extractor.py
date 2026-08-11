"""
function_block_extractor.py - Independent ABB function-block declaration counter.

Scans PC Diagram PDF text for functional control block declarations such as
PIDCON(...), MOTCON(...), VALVECON(...), and MANSTN(...).

Only declarations (name immediately followed by '(') are counted. Parameter
references, cross-references, signal names, and wire labels like
PIDCON1:55/940LC391:PARAM4 are ignored.

This module is intentionally isolated from the hardwired I/O extraction pipeline.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Mapping, Optional, Pattern, Tuple

# Extensible list — append new ABB block type names here.
SUPPORTED_FUNCTION_BLOCKS: Tuple[str, ...] = (
    "PIDCON",
    "MOTCON",
    "VALVECON",
    "MANSTN",
)

# name + optional whitespace (CAD/newline splits) + opening parenthesis
_BLOCK_PATTERN_TEMPLATE = r"\b{name}\s*\("


def _compile_patterns(
    block_names: Iterable[str] = SUPPORTED_FUNCTION_BLOCKS,
) -> Dict[str, Pattern[str]]:
    return {
        name: re.compile(_BLOCK_PATTERN_TEMPLATE.format(name=re.escape(name)), re.IGNORECASE)
        for name in block_names
    }


_COMPILED_PATTERNS = _compile_patterns()


def count_function_blocks(
    page_texts: Optional[Iterable[str]] = None,
    *,
    block_names: Iterable[str] = SUPPORTED_FUNCTION_BLOCKS,
) -> Dict[str, int]:
    """
    Count ABB function-block declarations across page text layers.

    Returns an ordered dict with every supported block name (count may be 0).
    Scans each page's merged text once to avoid double-counting overlapping layers.
    """
    names = tuple(block_names)
    counts: Dict[str, int] = {name: 0 for name in names}

    if not page_texts:
        return counts

    patterns = (
        _COMPILED_PATTERNS
        if names == SUPPORTED_FUNCTION_BLOCKS
        else _compile_patterns(names)
    )

    for text in page_texts:
        if not text:
            continue
        for name in names:
            counts[name] += len(patterns[name].findall(text))

    return counts


def function_block_summary_rows(
    counts: Optional[Mapping[str, int]] = None,
    *,
    block_names: Iterable[str] = SUPPORTED_FUNCTION_BLOCKS,
) -> List[Dict[str, object]]:
    """Build ordered summary rows for Excel export."""
    names = tuple(block_names)
    source = counts or {}
    return [
        {"Functional Block": name, "Total Count": int(source.get(name, 0))}
        for name in names
    ]
