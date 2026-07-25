"""
duplicate_detector.py - Stage 9: Deduplication of extracted 800-Series engineering I/O objects.
Primary Key: (io_family, card_number, channel_number, device_tag).
"""

from typing import List, Tuple, Set
from backend.pc_element.parser.grammar_parser import ParsedIOReference


class DuplicateDetector:
    """Detects and removes duplicate I/O reference objects based on Primary Key."""

    @classmethod
    def deduplicate_references(cls, references: List[ParsedIOReference]) -> Tuple[List[ParsedIOReference], int]:
        """Returns unique list of references and count of duplicate records removed."""
        seen_keys: Set[Tuple[str, int, int, str]] = set()
        unique_refs: List[ParsedIOReference] = []
        duplicates_count = 0

        for ref in references:
            # Primary Key composite tuple
            pk = (
                ref.io_family.upper(),
                ref.card_number,
                ref.channel_number,
                ref.device_tag.upper()
            )

            if pk in seen_keys:
                duplicates_count += 1
            else:
                seen_keys.add(pk)
                unique_refs.append(ref)

        return unique_refs, duplicates_count
