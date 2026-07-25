import pytest
from pathlib import Path
from backend.parser.pdf_text_extractor import PDFTextExtractor
from backend.parser.parser_service import ParserService
from backend.mapper.element_mapper import ElementMapper

def test_db_element_multi_block_layered_default_parsing():
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_ac450_db.pdf"
    extractor = PDFTextExtractor("test_job_mb")
    pages = extractor.extract_text_pages(sample_pdf)
    
    service = ParserService("test_job_mb")
    elements, stats, warnings = service.parse_document_pages(pages, file_name="sample_ac450_db.pdf")
    
    assert stats.raw_default_blocks_found >= 5
    assert stats.hardware_default_blocks >= 2  # DEFAULT AI, DEFAULT AO
    assert stats.software_default_blocks >= 2  # DEFAULT AIS, DEFAULT AOS
    assert stats.merged_profiles_created >= 5
    assert stats.objects_parsed >= 8
    assert stats.inherited_parameters > 0
    assert stats.object_overrides > 0

    tags = [e.tag for e in elements]
    assert "AI1.1" in tags
    assert "AO2.1" in tags
    assert "PIDCON1" in tags
    assert "MOTCON1" in tags

    # Verify AI1.1 inherited BOTH Hardware (DEFAULT AI) and Software (DEFAULT AIS) defaults!
    ai1_1 = next(e for e in elements if e.tag == "AI1.1")
    assert ai1_1.get_parameter("NAME") == "BOILER_PRESS_TR_01"
    assert ai1_1.get_parameter("TYPE") == "ANALOG_INPUT" # Inherited from Hardware DEFAULT AI
    assert ai1_1.get_parameter("SCANT") == "1s"          # Inherited from Hardware DEFAULT AI
    assert ai1_1.get_parameter("DEC") == 2               # Inherited from Software DEFAULT AIS
    assert ai1_1.get_parameter("ERR_TR") == 0            # Inherited from Software DEFAULT AIS
    assert ai1_1.get_parameter("UNIT") == "BAR"          # Explicit Object Override

    # Verify AO2.1 inherited DEFAULT AO (Hardware) + DEFAULT AOS (Software)
    ao2_1 = next(e for e in elements if e.tag == "AO2.1")
    assert ao2_1.get_parameter("TYPE") == "OUTPUT_4_20MA" # Inherited from Hardware DEFAULT AO
    assert ao2_1.get_parameter("DEC") == 2                # Inherited from Software DEFAULT AOS

    # Verify mapping
    mapper = ElementMapper("test_job_mb")
    sheets = mapper.group_and_map(elements)
    assert "AI" in sheets
    assert "AO" in sheets
    assert "PIDCON" in sheets

def test_4_tier_hierarchical_ast_inheritance():
    # Synthetic page text with Hardware Default, Signal Default, Card Node (AI1 AI), and Object (AI1.4)
    pages = [
        {
            "page_number": 1,
            "text": """
DEFAULT AI
  :TYPE "ANALOG_INPUT"
  :SERVICE YES
  :SCANT "1s"

DEFAULT AIS
  :UNIT "%"
  :DEC 1
  :RANGEMAX 100.0

AI1 AI
  :ADDR 32
  :CONV_PAR "4..20mA"

AI1.4
  :NAME "PRESSURE_SENS_04"
  :UNIT "bar"
  :RANGEMAX 16.0
"""
        }
    ]

    service = ParserService("test_job_ast_4tier")
    elements, stats, warnings = service.parse_document_pages(pages, file_name="ast_test.pdf")

    # Card Node 'AI1 AI' MUST NOT be exported as an object!
    tags = [e.tag for e in elements]
    assert "AI1.4" in tags
    assert "AI1" not in tags, "Card Node AI1 MUST NOT be exported to Excel as a signal element"

    # AI1.4 MUST inherit in 4-tier order: Hardware (DEFAULT AI) -> Software (DEFAULT AIS) -> Card (AI1) -> Object (AI1.4)
    ai1_4 = next(e for e in elements if e.tag == "AI1.4")
    
    # 1. Hardware Defaults
    assert ai1_4.get_parameter("TYPE") == "ANALOG_INPUT"
    assert ai1_4.get_parameter("SERVICE") is True
    assert ai1_4.get_parameter("SCANT") == "1s"

    # 2. Software Defaults
    assert ai1_4.get_parameter("DEC") == 1

    # 3. Card Parameters (inherited from AI1 AI Card Node!)
    assert ai1_4.get_parameter("ADDR") == 32
    assert ai1_4.get_parameter("CONV_PAR") == "4..20mA"

    # 4. Explicit Object Parameters (Highest priority override!)
    assert ai1_4.get_parameter("NAME") == "PRESSURE_SENS_04"
    assert ai1_4.get_parameter("UNIT") == "bar"           # Overrides AIS default "%"
    assert ai1_4.get_parameter("RANGEMAX") == 16.0        # Overrides AIS default 100.0
