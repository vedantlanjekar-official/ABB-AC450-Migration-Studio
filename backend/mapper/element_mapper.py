from typing import List, Dict, Any
from backend.models.db_element import DBElement
from backend.core.logging import get_logger

class ElementMapper:
    """
    Groups parsed DB Elements by element type and maps dynamic key-value parameters
    into structured tabular datasets.
    
    Guarantees that default parameter values fill all empty/null cells per worksheet.
    """
    
    # Preferred initial column order for industrial readability
    PRIORITY_COLUMNS = ["Tag", "Index", "NAME", "DESCR", "UNIT", "RANGEMIN", "RANGEMAX", "TYPE", "ACTUAL"]

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def group_and_map(self, elements: List[DBElement]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups elements by element_type and returns a dict mapping
        sheet_name -> list of row dicts with zero blank cells for defaulted parameters.
        """
        grouped_elements: Dict[str, List[DBElement]] = {}
        for elem in elements:
            elem_type = elem.element_type.upper()
            if elem_type not in grouped_elements:
                grouped_elements[elem_type] = []
            grouped_elements[elem_type].append(elem)

        mapped_sheets: Dict[str, List[Dict[str, Any]]] = {}

        for elem_type, elem_list in grouped_elements.items():
            # 1. Gather all unique parameter keys across all elements of this type
            all_keys = set()
            for elem in elem_list:
                all_keys.update(elem.parameters.keys())

            # 2. Build default parameter lookup dict for this sheet family
            family_default_values: Dict[str, Any] = {}
            for col in all_keys:
                for elem in elem_list:
                    val = elem.parameters.get(col)
                    if val not in (None, ""):
                        family_default_values[col] = val
                        break

            # 3. Determine column ordering
            ordered_keys = [k for k in self.PRIORITY_COLUMNS if k in all_keys or k in ("Tag", "Index")]
            remaining_keys = sorted([k for k in all_keys if k not in self.PRIORITY_COLUMNS])
            final_columns = ["Tag", "Index"] + [k for k in ordered_keys if k not in ("Tag", "Index")] + remaining_keys

            rows = []
            for elem in elem_list:
                row = {
                    "Tag": elem.tag,
                    "Index": elem.element_index,
                }
                # Add all parameters, populating empty cells with sheet default values
                for col in final_columns:
                    if col not in ("Tag", "Index"):
                        val = elem.parameters.get(col)
                        if (val is None or val == "") and col in family_default_values:
                            val = family_default_values[col]
                        row[col] = val if val is not None else ""
                rows.append(row)

            mapped_sheets[elem_type] = rows
            self.logger.info(f"Grouped {len(rows)} objects under sheet type '{elem_type}' with {len(final_columns)} columns (defaults filled).")

        return mapped_sheets
