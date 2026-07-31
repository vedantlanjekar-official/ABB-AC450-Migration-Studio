from typing import List, Dict, Any
from backend.models.db_element import DBElement
from backend.constants.ac450_constants import KNOWN_ELEMENT_TYPES
from backend.mapper.record_clubber import derive_loop_tag
from backend.core.logging import get_logger

class ElementMapper:
    """
    Groups parsed DB Elements by element type and maps dynamic key-value parameters
    into structured tabular datasets.
    
    Guarantees that each object's own inherited parameters are written as-is.
    Does NOT copy parameter values from sibling objects into blank cells.
    Preserves input element order (RecordClubber Loop Tag clubbing order).
    """
    
    # Preferred initial column order for industrial readability
    PRIORITY_COLUMNS = [
        "Tag", "Index", "NAME", "Loop Tag", "DESCR",
        "UNIT", "RANGEMIN", "RANGEMAX", "TYPE", "ACTUAL",
    ]

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def _group_by_type(self, elements: List[DBElement]) -> Dict[str, List[DBElement]]:
        grouped: Dict[str, List[DBElement]] = {}
        for elem in elements:
            elem_type = elem.element_type.upper()
            grouped.setdefault(elem_type, []).append(elem)
        return grouped

    def _build_type_sheet_context(
        self, elem_list: List[DBElement]
    ) -> List[str]:
        """Return column order for a homogeneous element list (no sibling defaults)."""
        all_keys: set[str] = set()
        for elem in elem_list:
            all_keys.update(elem.parameters.keys())

        ordered_keys = [
            k for k in self.PRIORITY_COLUMNS
            if k in all_keys or k in ("Tag", "Index", "Loop Tag")
        ]
        remaining_keys = sorted([
            k for k in all_keys
            if k not in self.PRIORITY_COLUMNS and k != "Loop Tag"
        ])
        final_columns = (
            ["Tag", "Index"]
            + [k for k in ordered_keys if k not in ("Tag", "Index")]
            + remaining_keys
        )
        if "Loop Tag" not in final_columns:
            if "NAME" in final_columns:
                name_idx = final_columns.index("NAME")
                final_columns.insert(name_idx + 1, "Loop Tag")
            else:
                final_columns.insert(2, "Loop Tag")

        return final_columns

    def map_clubbed(self, elements: List[DBElement]) -> List[Dict[str, Any]]:
        """
        Map clubbed elements into a single flat row list for one consolidated worksheet.

        Preserves club order (Loop Tag groups: AI→AO, DO→DI, …). Each row includes
        Category plus that object's own parameters only — blank cells stay blank.
        """
        if not elements:
            return []

        grouped_elements = self._group_by_type(elements)
        type_columns: Dict[str, List[str]] = {}
        for elem_type, elem_list in grouped_elements.items():
            type_columns[elem_type] = self._build_type_sheet_context(elem_list)

        all_keys: set[str] = {"Category"}
        for cols in type_columns.values():
            all_keys.update(cols)

        unified_columns = ["Category"]
        for key in self.PRIORITY_COLUMNS:
            if key in all_keys and key not in unified_columns:
                unified_columns.append(key)
        # DESCR must always exist so category indicators can sit immediately after it
        if "DESCR" not in unified_columns:
            if "Loop Tag" in unified_columns:
                unified_columns.insert(unified_columns.index("Loop Tag") + 1, "DESCR")
            elif "NAME" in unified_columns:
                unified_columns.insert(unified_columns.index("NAME") + 1, "DESCR")
            else:
                unified_columns.append("DESCR")
        unified_columns += sorted(k for k in all_keys if k not in unified_columns)

        rows: List[Dict[str, Any]] = []
        for elem in elements:
            name_val = elem.parameters.get("NAME")
            name_str = str(name_val).strip() if name_val not in (None, "") else ""
            row_data: Dict[str, Any] = {
                "Category": elem.element_type.upper(),
                "Tag": elem.tag,
                "Index": elem.element_index,
                "Loop Tag": derive_loop_tag(name_str),
                "DESCR": elem.parameters.get("DESCR", ""),
            }
            if row_data["DESCR"] is None:
                row_data["DESCR"] = ""
            for col in unified_columns:
                if col in ("Category", "Tag", "Index", "Loop Tag", "DESCR"):
                    continue
                val = elem.parameters.get(col)
                row_data[col] = val if val is not None else ""
            rows.append({col: row_data.get(col, "") for col in unified_columns})

        self.logger.info(
            f"Mapped {len(rows)} clubbed object(s) into a single worksheet "
            f"with {len(unified_columns)} columns."
        )
        return rows

    def group_and_map(self, elements: List[DBElement]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups elements by element_type and returns a dict mapping
        sheet_name -> list of row dicts using each object's own parameters only.
        Row order within each sheet matches the order of `elements` (clubbed order).
        """
        grouped_elements = self._group_by_type(elements)
        mapped_sheets: Dict[str, List[Dict[str, Any]]] = {}

        sheet_order = [t for t in KNOWN_ELEMENT_TYPES if t in grouped_elements]
        sheet_order += [t for t in grouped_elements if t not in sheet_order]

        for elem_type in sheet_order:
            elem_list = grouped_elements[elem_type]
            final_columns = self._build_type_sheet_context(elem_list)

            rows = []
            for elem in elem_list:
                name_val = elem.parameters.get("NAME")
                name_str = str(name_val).strip() if name_val not in (None, "") else ""
                row_data = {
                    "Tag": elem.tag,
                    "Index": elem.element_index,
                    "Loop Tag": derive_loop_tag(name_str),
                }
                for col in final_columns:
                    if col in ("Tag", "Index", "Loop Tag"):
                        continue
                    val = elem.parameters.get(col)
                    row_data[col] = val if val is not None else ""
                ordered_row = {col: row_data.get(col, "") for col in final_columns}
                rows.append(ordered_row)

            mapped_sheets[elem_type] = rows
            self.logger.info(
                f"Grouped {len(rows)} objects under sheet type '{elem_type}' "
                f"with {len(final_columns)} columns."
            )

        return mapped_sheets
