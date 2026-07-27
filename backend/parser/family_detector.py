import re
from typing import Optional
from backend.core.logging import get_logger

class FamilyDetector:
    """
    Stage 3 — Dynamic Family Boundary Detector Module.
    Identifies element family transitions for supported I/O types
    (AI, AO, DI, DO, AI800, AO800, DI800, DO800) from default headers,
    card definitions, and object declarations. Unsupported families may still
    be detected here but are filtered out by ParserService / ElementValidator.
    """

    DEFAULT_FAMILY_REGEX = re.compile(
        r'^\s*DEFAULT[S]?[:\s\-]+([A-Z0-9_]+(?:\([A-Z0-9_]+\))?)\b',
        re.IGNORECASE
    )

    CARD_FAMILY_REGEX = re.compile(
        r'^\s*((?:AI800|AO800|DI800|DO800|[A-Z]{2,12})\d+)\s+((?:AI800|AO800|DI800|DO800|[A-Z]{2,12})(?:\([A-Z0-9_]+\))?)\b',
        re.IGNORECASE
    )

    OBJECT_FAMILY_REGEX = re.compile(
        r'^\s*(AI800|AO800|DI800|DO800|[A-Z]{2,12})\d+(?:\.\d+)*\b',
        re.IGNORECASE
    )

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def normalize_family_name(self, raw_name: str) -> str:
        """
        Normalizes raw default block or object family names into standard family keys.
        e.g., AIS -> AI, AOS -> AO, DIS -> DI, DOS -> DO,
              AI800S -> AI800, AO800S -> AO800.
        """
        if not raw_name:
            return ""
        clean = re.sub(r'\(.*?\)', '', raw_name.strip()).strip().upper()
        # Prefer known 800-series base names before stripping trailing S
        for fam_800 in ("AI800", "AO800", "DI800", "DO800"):
            if clean == fam_800 or clean == f"{fam_800}S":
                return fam_800
        if len(clean) > 2 and clean.endswith("S") and clean not in ("DS", "TEXT"):
            return clean[:-1]
        return clean

    def detect_family(self, line: str) -> Optional[str]:
        """Detects the normalized element family name from a line string."""
        line_str = line.strip()

        # 1. Check DEFAULT headers (e.g. DEFAULT AI, DEFAULT AIS, DEFAULT DAT(B), DEFAULT TEXT(20))
        match_def = self.DEFAULT_FAMILY_REGEX.match(line_str)
        if match_def:
            return self.normalize_family_name(match_def.group(1))

        if line_str.upper().startswith("DEFAULT"):
            parts = line_str.split()
            if len(parts) >= 2:
                raw_name = parts[1].strip(":-_")
                if raw_name and raw_name.upper() not in ("OF", "DEFAULTS", "BLOCK", "SECTION"):
                    return self.normalize_family_name(raw_name)

        # 2. Check Card definitions (e.g. AI1 AI, AO2 AO, DI1 DI, DAT1 DAT(B))
        match_card = self.CARD_FAMILY_REGEX.match(line_str)
        if match_card:
            card_prefix = match_card.group(1).upper()
            suffix_fam = self.normalize_family_name(match_card.group(2))
            base_fam = re.match(r'^([A-Z]{2,12})', card_prefix)
            if base_fam:
                prefix_fam = base_fam.group(1).upper()
                if prefix_fam == suffix_fam or suffix_fam in prefix_fam:
                    return suffix_fam
                return prefix_fam
            return suffix_fam

        # 3. Check Object declarations (e.g. AI1.1, AO2.1, PIDCON1, DAT1)
        match_obj = self.OBJECT_FAMILY_REGEX.match(line_str)
        if match_obj:
            return self.normalize_family_name(match_obj.group(1))

        return None
