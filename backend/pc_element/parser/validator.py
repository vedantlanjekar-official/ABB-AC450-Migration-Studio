"""
validator.py - Stage 10: Validation of EngineeringIO objects for PC Element Engine.
Mandatory fields: io_family, category, card_number (>=0; 0 = unknown/soft AAX), device_tag, loop_tag.
Only the eight supported I/O families are accepted.
"""

from typing import List, Tuple, Set
import re
from pydantic import BaseModel, Field


class EngineeringIO(BaseModel):
    io_family: str
    io_type: str
    category: str
    card_number: int
    channel_number: int
    loop_tag: str
    device_tag: str
    description: str = ""
    controller: str = ""
    process_area: str = ""
    page_number: int = 1
    source_reference: str = ""


class Validator:
    """Validates extracted EngineeringIO objects."""

    VALID_FAMILIES: Set[str] = {
        "AI800_", "AO800_", "DI800_", "DO800_",
        "AI", "AO", "DI", "DO",
    }

    VALID_CATEGORIES: Set[str] = {
        "AI800", "AO800", "DI800", "DO800",
        "AI", "AO", "DI", "DO",
    }

    @classmethod
    def validate_object(cls, obj: EngineeringIO) -> Tuple[bool, List[str]]:
        """Validates a single EngineeringIO object and returns (is_valid, errors)."""
        errors: List[str] = []

        family = (obj.io_family or "").upper()
        if family not in cls.VALID_FAMILIES:
            errors.append(f"Invalid or missing io_family: '{obj.io_family}'")

        category = (obj.category or "").upper()
        if category not in cls.VALID_CATEGORIES:
            errors.append(f"Invalid or missing category: '{obj.category}'")

        if obj.card_number < 0:
            errors.append(f"Invalid card_number: {obj.card_number}")

        if obj.channel_number < 0:
            errors.append(f"Invalid channel_number: {obj.channel_number}")

        if not obj.device_tag or not obj.device_tag.strip():
            errors.append("Missing mandatory device_tag")
        elif not re.search(r'[A-Za-z]', obj.device_tag):
            errors.append(f"device_tag must contain letters, got numeric '{obj.device_tag}'")

        if not obj.loop_tag or not obj.loop_tag.strip():
            errors.append("Missing mandatory loop_tag")
        elif not re.search(r'[A-Za-z]', obj.loop_tag):
            errors.append(f"loop_tag must contain letters, got numeric '{obj.loop_tag}'")

        return len(errors) == 0, errors

    @classmethod
    def filter_and_validate_all(cls, objects: List[EngineeringIO]) -> Tuple[List[EngineeringIO], List[str]]:
        """Filters a list of EngineeringIO objects, returning valid objects and accumulated error messages."""
        valid_list: List[EngineeringIO] = []
        all_warnings: List[str] = []

        for item in objects:
            is_valid, errors = cls.validate_object(item)
            if is_valid:
                valid_list.append(item)
            else:
                warn_msg = f"Skipping invalid I/O object '{item.source_reference}': {', '.join(errors)}"
                all_warnings.append(warn_msg)

        return valid_list, all_warnings
