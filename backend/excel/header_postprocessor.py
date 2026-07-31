"""Final exported-workbook header transformations."""

from __future__ import annotations

from typing import Mapping

from openpyxl.workbook.workbook import Workbook


DB_HEADER_MAPPING: Mapping[str, str] = {
    "NAME": "$(DEVICETAG)",
    "LOOP TAG": "$(TAG)",
    "DESCR": "$(NAME_40)",
    "UNIT": "$(DEVICETAG:UNIT)",
    "RANGE MIN": "$(DEVICETAG:MIN)",
    "RANGEMIN": "$(DEVICETAG:MIN)",
    "RANGE MAX": "$(DEVICETAG:MAX)",
    "RANGEMAX": "$(DEVICETAG:MAX)",
}

PC_HEADER_MAPPING: Mapping[str, str] = {
    "LOOP TAG": "$(TAG)",
    "DEVICE TAG": "$(DEVICETAG)",
    "DESCR": "$(NAME_40)",
    "DESCRIPTION": "$(NAME_40)",
}


def rename_export_headers(
    workbook: Workbook,
    mapping: Mapping[str, str],
    header_row: int,
) -> None:
    """Rename header cells without changing data, styles, or column order."""
    for worksheet in workbook.worksheets:
        for cell in worksheet[header_row]:
            if cell.value is None:
                continue
            normalized = " ".join(str(cell.value).split()).upper()
            replacement = mapping.get(normalized)
            if replacement:
                cell.value = replacement
