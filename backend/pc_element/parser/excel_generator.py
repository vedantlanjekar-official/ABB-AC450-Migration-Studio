"""
excel_generator.py - Stage 11: Excel Generator for PC Element Engineering I/O Lists.

Columns:
  Sr. No. | Loop Tag | Description | Device Tag | Category | Slot/Card | Channel
"""

from typing import List, Any
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from backend.pc_element.parser.validator import EngineeringIO


def sanitize_cell_value(val: Any) -> Any:
    """Sanitizes cell values to prevent openpyxl from treating strings starting with = or - as Excel formulas."""
    if val is None:
        return ""
    if isinstance(val, str):
        s = val.lstrip('=+@').strip()
        if s.startswith('-') and len(s) > 1 and s[1].isalpha():
            s = s[1:].strip()
        return s
    return val


class ExcelGenerator:
    """Generates Valmet-compatible Excel workbooks for PC Element I/O lists."""

    FAMILY_SORT_ORDER = {
        "AI800_": 1,
        "AI": 2,
        "AO800_": 3,
        "AO": 4,
        "DI800_": 5,
        "DI": 6,
        "DO800_": 7,
        "DO": 8,
    }

    @classmethod
    def generate_excel(cls, io_objects: List[EngineeringIO], output_path: str) -> str:
        """Generates styled Excel workbook at output_path and returns the filepath."""
        sorted_objects = sorted(
            io_objects,
            key=lambda x: (
                cls.FAMILY_SORT_ORDER.get(x.io_family.upper(), 99),
                x.card_number,
                x.channel_number,
                x.loop_tag,
                x.device_tag,
            )
        )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "I_O_List"
        ws.views.sheetView[0].showGridLines = True

        header_fill = PatternFill(start_color="00805A", end_color="00805A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Segoe UI", size=14, bold=True, color="004D36")
        subtitle_font = Font(name="Segoe UI", size=10, italic=True, color="4A5568")
        data_font = Font(name="Segoe UI", size=10, color="1A202C")
        zebra_fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")

        thin_side = Side(style="thin", color="CBD5E0")
        thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")

        ws.merge_cells("A1:G1")
        ws["A1"] = "VALMET ENGINEERING I/O MIGRATION LIST"
        ws["A1"].font = title_font
        ws["A1"].alignment = left_align

        ws.merge_cells("A2:G2")
        ws["A2"] = "ABB Advant Controller AC450 — PC Element Hardwired I/O References"
        ws["A2"].font = subtitle_font
        ws["A2"].alignment = left_align

        headers = [
            "Sr. No.",
            "Loop Tag",
            "Description",
            "Device Tag",
            "Category",
            "Slot/Card",
            "Channel",
        ]

        start_row = 4
        for col_idx, header_text in enumerate(headers, start=1):
            cell = ws.cell(row=start_row, column=col_idx, value=header_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border
        ws.row_dimensions[start_row].height = 26

        current_row = start_row + 1
        for sr_no, obj in enumerate(sorted_objects, start=1):
            channel_val = obj.channel_number if obj.channel_number > 0 else ""
            row_data = [
                sr_no,
                obj.loop_tag,
                obj.description or "",
                obj.device_tag,
                obj.category,
                obj.card_number,
                channel_val,
            ]

            fill_to_apply = zebra_fill if (sr_no % 2 == 0) else None

            for col_idx, val in enumerate(row_data, start=1):
                if col_idx == 1 or col_idx in (6, 7):
                    clean_val = val if val != "" else ""
                else:
                    clean_val = sanitize_cell_value(val)
                    if clean_val is None:
                        clean_val = ""
                cell = ws.cell(row=current_row, column=col_idx, value=clean_val)
                cell.font = data_font
                cell.border = thin_border

                if isinstance(clean_val, str):
                    cell.data_type = 's'

                if fill_to_apply:
                    cell.fill = fill_to_apply

                if col_idx in (1, 5, 6, 7):
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align

            ws.row_dimensions[current_row].height = 20
            current_row += 1

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row < start_row:
                    continue
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        if os.path.dirname(output_path):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        wb.save(output_path)
        return output_path
