from typing import Dict, Any, Tuple
from backend.core.logging import get_logger

class MergeEngine:
    """
    Applies compiled family default profiles into explicit DB element objects.
    
    Precedence & Fallback Rules:
      1. Explicit Object Non-Empty Value (highest priority)
      2. Merged Family Default Profile Value (fills blank/missing object cells)
      3. Blank (only if both object and default are blank/empty)
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def merge_object_with_family_defaults(
        self,
        explicit_object_params: Dict[str, Any],
        family_defaults: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Merges compiled family defaults into explicit object parameters.
        Guarantees that default data is printed wherever the explicit object cell is blank or omitted.
        
        Args:
            explicit_object_params: Object's explicit parameters dictionary
            family_defaults: Compiled family default profile dictionary
            
        Returns:
            Tuple of (final_merged_parameters, inherited_count, overrides_count)
        """
        final_params: Dict[str, Any] = {}

        # 1. Populate initial defaults from family profile (uppercase keys)
        if family_defaults:
            for k, v in family_defaults.items():
                final_params[k.upper()] = v

        overrides_count = 0
        inherited_count = 0

        # 2. Merge explicit object parameters
        for k, v in explicit_object_params.items():
            norm_key = k.upper()
            val_str = str(v).strip() if v is not None else ""

            if val_str != "":
                # Object has an explicit non-empty value -> Overrides default!
                final_params[norm_key] = v
                overrides_count += 1
            else:
                # Object value is blank. If default has a non-empty value, keep default!
                if norm_key in final_params and str(final_params[norm_key]).strip() != "":
                    inherited_count += 1
                else:
                    final_params[norm_key] = v

        # 3. Count inherited defaults for keys omitted entirely from explicit object parameters
        if family_defaults:
            for def_key, def_val in family_defaults.items():
                norm_def_key = def_key.upper()
                if norm_def_key not in explicit_object_params and str(def_val).strip() != "":
                    inherited_count += 1

        return final_params, inherited_count, overrides_count
