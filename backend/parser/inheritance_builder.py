from typing import Dict, Any, Tuple, List, Set
from dataclasses import dataclass
from backend.core.logging import get_logger

@dataclass
class InheritanceProfileSummary:
    raw_blocks_found: int = 0
    hardware_blocks_count: int = 0
    software_blocks_count: int = 0
    standalone_blocks_count: int = 0
    merged_profiles_count: int = 0

class InheritanceBuilder:
    """
    Combines raw DEFAULT blocks into family inheritance profiles.
    
    Dynamic Family Grouping Rules:
      - AI Family    = DEFAULT AI (Hardware) + DEFAULT AIS (Software)
      - AO Family    = DEFAULT AO (Hardware) + DEFAULT AOS (Software)
      - DI Family    = DEFAULT DI (Hardware) + DEFAULT DIS (Software)
      - DO Family    = DEFAULT DO (Hardware) + DEFAULT DOS (Software)
      - AI800 Family = DEFAULT AI800 + DEFAULT AI800S
      - AO800 Family = DEFAULT AO800 + DEFAULT AO800S
      - DI800 Family = DEFAULT DI800 + DEFAULT DI800S
      - DO800 Family = DEFAULT DO800 + DEFAULT DO800S
      - Single-block Families = DEFAULT <FAMILY>
    """

    KNOWN_FAMILIES = ["AI", "AO", "DI", "DO", "AI800", "AO800", "DI800", "DO800"]
    SOFTWARE_SUFFIXES = ["S", "CS", "DS"]

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def build_merged_profiles(
        self,
        raw_defaults: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Dict[str, Any]], InheritanceProfileSummary]:
        """
        Combines related default blocks into merged family default profiles.
        """
        summary = InheritanceProfileSummary(raw_blocks_found=len(raw_defaults))
        merged_profiles: Dict[str, Dict[str, Any]] = {}
        processed_raw_keys: Set[str] = set()

        if not raw_defaults:
            return merged_profiles, summary

        # 1. Classify raw blocks
        for block_name in raw_defaults.keys():
            upper_name = block_name.upper()
            if upper_name in self.KNOWN_FAMILIES:
                summary.hardware_blocks_count += 1
            elif any(upper_name == f + "S" or upper_name == f + "CS" for f in self.KNOWN_FAMILIES):
                summary.software_blocks_count += 1
            else:
                summary.standalone_blocks_count += 1

        # 2. Build multi-block family profiles for known families
        for family in self.KNOWN_FAMILIES:
            family_profile: Dict[str, Any] = {}
            has_blocks = False

            # First add Hardware defaults (e.g. AI)
            if family in raw_defaults:
                has_blocks = True
                processed_raw_keys.add(family)
                family_profile.update(raw_defaults[family])

            # Next add Software defaults (e.g. AIS, AICS) - Software overrides overlapping hardware keys
            sw_key = family + "S"
            if sw_key in raw_defaults:
                has_blocks = True
                processed_raw_keys.add(sw_key)
                family_profile.update(raw_defaults[sw_key])

            if has_blocks:
                merged_profiles[family] = family_profile
                self.logger.info(
                    f"Created combined inheritance profile for '{family}' "
                    f"with {len(family_profile)} default parameter(s)."
                )

        # 3. Build profiles for any remaining raw blocks (standalone families like PIDCON, MOTCON, DS, DAT, TEXT)
        for block_name, params in raw_defaults.items():
            upper_name = block_name.upper()
            if upper_name not in processed_raw_keys:
                merged_profiles[upper_name] = dict(params)
                processed_raw_keys.add(upper_name)
                self.logger.info(
                    f"Created standalone inheritance profile for '{upper_name}' with {len(params)} default parameter(s)."
                )

        summary.merged_profiles_count = len(merged_profiles)
        self.logger.info(
            f"InheritanceBuilder created {summary.merged_profiles_count} merged family profiles "
            f"from {summary.raw_blocks_found} raw DEFAULT blocks."
        )

        return merged_profiles, summary
