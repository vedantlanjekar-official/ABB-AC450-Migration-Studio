"""
metadata_extractor.py - Stage 7 & 8: Extracting Controller and Process Area from drawing title blocks.
"""

from typing import List, Dict, Optional, Tuple
import re
from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    controller: str = ""
    process_area: str = ""
    project_name: str = ""


class MetadataExtractor:
    """Extracts Controller and Process Area metadata from title blocks."""

    CONTROLLER_PATTERN = re.compile(
        r'\b(?:PM\d+|NODE\d+|AC450|CONTROLLER)\s*[\/\\]\s*(?:NODE\d+|PM\d+|\w+)',
        re.IGNORECASE
    )
    ALT_CONTROLLER_PATTERN = re.compile(
        r'\b(PM\d+[\/\\]Node\d+)\b',
        re.IGNORECASE
    )

    PROCESS_AREA_KEYWORDS = [
        "White Water System",
        "White water system",
        "Stock Preparation",
        "Felt Water Tank",
        "Paper Machine",
        "Drying Section",
        "Vacuum System",
        "Refiner System",
        "Screening Area",
        "Chest System"
    ]

    @classmethod
    def extract_metadata_from_pages(cls, page_texts: List[str]) -> DocumentMetadata:
        """Scans page text for Controller and Process Area."""
        controller = ""
        process_area = ""
        project_name = ""

        full_doc_text = "\n".join(page_texts)

        # 1. Search for Controller (e.g. PM2\Node22 or PM2/Node22)
        match = cls.ALT_CONTROLLER_PATTERN.search(full_doc_text)
        if not match:
            match = cls.CONTROLLER_PATTERN.search(full_doc_text)

        if match:
            controller = match.group(0).replace('\\', '/').strip()

        # 2. Search for Process Area in title blocks
        for page_text in page_texts:
            lines = [l.strip() for l in page_text.splitlines() if l.strip()]
            for idx, line in enumerate(lines):
                if "white water system" in line.lower():
                    process_area = "White water system"
                    break
                if "PC DIAGRAM" in line.upper() or "PM2" in line:
                    # Look at next 1-4 lines for process area text
                    for sub in lines[idx:idx+5]:
                        for kw in cls.PROCESS_AREA_KEYWORDS:
                            if kw.lower() in sub.lower():
                                process_area = sub
                                break
                        if process_area:
                            break
            if process_area:
                break

        # Fallback process area keyword search
        if not process_area:
            for kw in cls.PROCESS_AREA_KEYWORDS:
                if re.search(r'\b' + re.escape(kw) + r'\b', full_doc_text, re.IGNORECASE):
                    process_area = kw
                    break

        return DocumentMetadata(
            controller=controller,
            process_area=process_area,
            project_name=project_name
        )
