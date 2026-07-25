import pytest
import openpyxl
from pathlib import Path
from backend.excel.excel_generator import ExcelGenerator
from backend.parser.pdf_text_extractor import PDFTextExtractor
from backend.parser.parser_service import ParserService
from backend.mapper.element_mapper import ElementMapper

def test_excel_workbook_generation(tmp_path):
    mapped_sheets = {
        "AI": [
            {"Tag": "AI1.1", "Index": "1.1", "NAME": "PRESS_01", "UNIT": "BAR", "RANGEMAX": 100.0},
            {"Tag": "AI1.2", "Index": "1.2", "NAME": "PRESS_02", "UNIT": "BAR", "RANGEMAX": 200.0}
        ],
        "PIDCON": [
            {"Tag": "PIDCON1", "Index": "1", "NAME": "CTRL_01", "GAIN": 2.5, "MODE": "AUTO"}
        ]
    }
    
    out_file = tmp_path / "test_out.xlsx"
    generator = ExcelGenerator("test_job_3")
    sheets = generator.generate_workbook(mapped_sheets, out_file)
    
    assert out_file.exists()
    assert "AI" in sheets
    assert "PIDCON" in sheets
    
    wb = openpyxl.load_workbook(out_file)
    assert "AI" in wb.sheetnames
    assert "PIDCON" in wb.sheetnames
    
    ws_ai = wb["AI"]
    assert ws_ai.cell(row=1, column=1).value == "Tag"
    assert ws_ai.cell(row=2, column=1).value == "AI1.1"
    assert ws_ai.cell(row=2, column=3).value == "PRESS_01"

def test_excel_default_values_printed_in_blank_cells(tmp_path):
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_ac450_db.pdf"
    extractor = PDFTextExtractor("test_excel_defaults")
    pages = extractor.extract_text_pages(sample_pdf)
    
    parser = ParserService("test_excel_defaults")
    elements, stats, _ = parser.parse_document_pages(pages, "sample_ac450_db.pdf")
    
    mapper = ElementMapper("test_excel_defaults")
    mapped_sheets = mapper.group_and_map(elements)
    
    out_excel = tmp_path / "valmet_defaults_export.xlsx"
    generator = ExcelGenerator("test_excel_defaults")
    generator.generate_workbook(mapped_sheets, out_excel)
    
    wb = openpyxl.load_workbook(out_excel)
    ws_ai = wb["AI"]
    
    # Read headers
    headers = [ws_ai.cell(row=1, column=col).value for col in range(1, ws_ai.max_column + 1)]
    assert "TYPE" in headers
    assert "SCANT" in headers
    assert "DEC" in headers
    assert "ERR_TR" in headers
    
    # Get column indices (1-based)
    type_col = headers.index("TYPE") + 1
    scant_col = headers.index("SCANT") + 1
    dec_col = headers.index("DEC") + 1
    
    # AI1.1 is row 2
    # TYPE was omitted in AI1.1 object text, inherited from DEFAULT AI ("ANALOG_INPUT")
    # SCANT was omitted in AI1.1 object text, inherited from DEFAULT AI ("1s")
    # DEC was omitted in AI1.1 object text, inherited from DEFAULT AIS (2)
    assert ws_ai.cell(row=2, column=type_col).value == "ANALOG_INPUT"
    assert ws_ai.cell(row=2, column=scant_col).value == "1s"
    assert ws_ai.cell(row=2, column=dec_col).value == 2

def test_excel_no_blank_cells_for_inherited_defaults():
    from backend.models.db_element import DBElement

    # AI1.1 has explicit TYPE, AI1.2 omits TYPE
    elements = [
        DBElement(
            tag="AI1.1",
            element_type="AI",
            element_index="1.1",
            parameters={"NAME": "SENS_1", "TYPE": "ANALOG_INPUT", "SCANT": "1s"}
        ),
        DBElement(
            tag="AI1.2",
            element_type="AI",
            element_index="1.2",
            parameters={"NAME": "SENS_2"}
        )
    ]

    mapper = ElementMapper("test_defaults_filling")
    sheets = mapper.group_and_map(elements)
    ai_rows = sheets["AI"]

    row_1 = next(r for r in ai_rows if r["Tag"] == "AI1.1")
    row_2 = next(r for r in ai_rows if r["Tag"] == "AI1.2")

    # Row 2 MUST NOT have empty string for TYPE or SCANT, it must take the sheet default value!
    assert row_2["TYPE"] == "ANALOG_INPUT"
    assert row_2["SCANT"] == "1s"
