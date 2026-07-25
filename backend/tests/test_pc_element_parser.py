"""
test_pc_element_parser.py - Unit tests for ABB AC450 PC Element Hardwired I/O Parser.
"""

import pytest
import os
import openpyxl
from backend.pc_element.parser.grammar_parser import GrammarParser
from backend.pc_element.parser.duplicate_detector import DuplicateDetector
from backend.pc_element.parser.validator import Validator, EngineeringIO
from backend.pc_element.parser.excel_generator import ExcelGenerator


def test_user_examples_extraction():
    """Test all explicit user example formats from the request prompt."""
    
    # Example 1: AI800_1.16/82M073.IT
    ref1 = GrammarParser.parse_reference("AI800_1.16/82M073.IT")
    assert ref1 is not None
    assert ref1.card_number == 1
    assert ref1.channel_number == 16
    assert ref1.loop_tag == "82M073"
    assert ref1.device_tag == "82M073.IT"
    assert ref1.io_type == "AI"
    assert ref1.io_family == "AI800_"

    # Example 2: DI800_1.15/82M073.RDY
    ref2 = GrammarParser.parse_reference("DI800_1.15/82M073.RDY")
    assert ref2 is not None
    assert ref2.card_number == 1
    assert ref2.channel_number == 15
    assert ref2.loop_tag == "82M073"
    assert ref2.device_tag == "82M073.RDY"
    assert ref2.io_type == "DI"

    # Example 3: AI800_5.10/82LIC660.MV
    ref3 = GrammarParser.parse_reference("AI800_5.10/82LIC660.MV")
    assert ref3 is not None
    assert ref3.card_number == 5
    assert ref3.channel_number == 10
    assert ref3.loop_tag == "82LIC660"
    assert ref3.device_tag == "82LIC660.MV"
    assert ref3.io_type == "AI"

    # Example 4: AO800_2.5/82LIC660.OUT
    ref4 = GrammarParser.parse_reference("AO800_2.5/82LIC660.OUT")
    assert ref4 is not None
    assert ref4.card_number == 2
    assert ref4.channel_number == 5
    assert ref4.loop_tag == "82LIC660"
    assert ref4.device_tag == "82LIC660.OUT"
    assert ref4.io_type == "AO"

    # Example 5: DO800_1.16/82M073.MSTR
    ref5 = GrammarParser.parse_reference("DO800_1.16/82M073.MSTR")
    assert ref5 is not None
    assert ref5.card_number == 1
    assert ref5.channel_number == 16
    assert ref5.loop_tag == "82M073"
    assert ref5.device_tag == "82M073.MSTR"
    assert ref5.io_type == "DO"

    # Diagram Drawing Example: -AI800_2.1/M49M021.CURR
    ref6 = GrammarParser.parse_reference("-AI800_2.1/M49M021.CURR")
    assert ref6 is not None
    assert ref6.card_number == 2
    assert ref6.channel_number == 1
    assert ref6.loop_tag == "M49M021"
    assert ref6.device_tag == "M49M021.CURR"
    assert ref6.io_type == "AI"


def test_excel_generation_columns(tmp_path):
    """Verify Excel output columns match exact user layout: Loop Tag, Tag Description, Device Tag, IO type, Controller, Process area."""
    obj1 = EngineeringIO(
        io_family="AO800_",
        io_type="AO",
        category="Analog Output",
        card_number=2,
        channel_number=5,
        loop_tag="82LIC660",
        device_tag="82LIC660.OUT",
        description="Felt Water Tank",
        controller="PM2/Node22",
        process_area="White water system"
    )
    obj2 = EngineeringIO(
        io_family="AI800_",
        io_type="AI",
        category="Analog Input",
        card_number=5,
        channel_number=10,
        loop_tag="82LIC660",
        device_tag="82LIC660.MV",
        description="Felt Water Tank",
        controller="PM2/Node22",
        process_area="White water system"
    )

    out_file = str(tmp_path / "test_io_list.xlsx")
    ExcelGenerator.generate_excel([obj1, obj2], out_file)
    assert os.path.exists(out_file)

    wb = openpyxl.load_workbook(out_file)
    ws = wb["I_O_List"]

    # Header in row 4
    headers = [ws.cell(row=4, column=c).value for c in range(1, 7)]
    expected_headers = ["Loop Tag", "Tag Description", "Device Tag", "IO type", "Controller", "Process area"]
    assert headers == expected_headers

    # Row 5 data
    row5 = [ws.cell(row=5, column=c).value for c in range(1, 7)]
    assert row5 == ["82LIC660", "Felt Water Tank", "82LIC660.MV", "AI", "PM2/Node22", "White water system"]

    # Row 6 data
    row6 = [ws.cell(row=6, column=c).value for c in range(1, 7)]
    assert row6 == ["82LIC660", "Felt Water Tank", "82LIC660.OUT", "AO", "PM2/Node22", "White water system"]


def test_pc_element_parser_service_pipeline(tmp_path):
    """Test the full PCParserService orchestrator pipeline with mock PDF content."""
    from unittest.mock import patch
    from backend.pc_element.parser.parser_service import PCParserService
    from backend.pc_element.parser.pdf_reader import PageContent

    mock_pages = [
        PageContent(
            page_number=1,
            text="-AI800_2.1/M49M021.CURR\nFelt Water Tank Level\nPM2\\Node22\nWhite Water System",
            raw_lines=[
                "-AI800_2.1/M49M021.CURR",
                "Felt Water Tank Level",
                "PM2\\Node22",
                "White Water System"
            ]
        )
    ]
    
    with patch('backend.pc_element.parser.parser_service.PDFReader.read_all_pages', return_value=mock_pages):
        service = PCParserService(
            file_path=__file__,
            job_id="test_job",
            output_dir=str(tmp_path)
        )
        res = service.execute_pipeline()
        
        assert len(res.errors) == 0
        assert res.total_io_found == 1
        assert res.ai800_count == 1
        assert res.controller_found == "PM2/Node22"
        assert res.process_area_found == "White water system"
        assert len(res.preview_data) == 1
        assert res.preview_data[0]["Loop Tag"] == "M49M021"

