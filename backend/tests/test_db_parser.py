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
    
    assert stats.raw_default_blocks_found >= 4  # AI/AIS/AO/AOS only (unsupported defaults skipped)
    assert stats.hardware_default_blocks >= 2  # DEFAULT AI, DEFAULT AO
    assert stats.software_default_blocks >= 2  # DEFAULT AIS, DEFAULT AOS
    assert stats.merged_profiles_created >= 2
    assert stats.objects_parsed >= 2
    assert stats.inherited_parameters > 0
    assert stats.object_overrides > 0

    tags = [e.tag for e in elements]
    types = {e.element_type.upper() for e in elements}
    assert "AI1.1" in tags
    assert "AO2.1" in tags
    # Unsupported engineering objects must be ignored entirely
    assert "PIDCON1" not in tags
    assert "MOTCON1" not in tags
    assert "VALVECON1" not in tags
    assert "DAT1" not in tags
    assert "TEXT1" not in tags
    assert types.issubset({"AI", "AO", "DI", "DO", "AI800", "AO800", "DI800", "DO800"})

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

    # Verify mapping — single consolidated worksheet with supported I/O categories only
    mapper = ElementMapper("test_job_mb")
    from backend.mapper.record_clubber import RecordClubber
    clubbed = RecordClubber("test_job_mb").club_elements(elements)
    rows = mapper.map_clubbed(clubbed)
    categories = {r["Category"] for r in rows}
    assert "AI" in categories
    assert "AO" in categories
    assert "PIDCON" not in categories
    assert categories.issubset({"AI", "AO", "DI", "DO", "AI800", "AO800", "DI800", "DO800"})

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


def test_unsupported_element_types_are_skipped():
    """Only the eight supported I/O families must be extracted."""
    pages = [
        {
            "page_number": 1,
            "text": """
DEFAULT AI
  :TYPE "ANALOG_INPUT"

DEFAULT AIS
  :UNIT "%"

AI1.1
  :NAME "AI_OK"

PIDCON1
  :NAME "CTRL_SKIP"
  :GAIN 2.5

AIC1
  :NAME "AIC_SKIP"

DAT1
  :NAME "DAT_SKIP"

MANSTN1
  :NAME "MAN_SKIP"

TEXT1
  :NAME "TEXT_SKIP"

DI8001.1
  :NAME "DI800_OK"

AO8002.1
  :NAME "AO800_OK"
"""
        }
    ]

    service = ParserService("test_job_filter")
    elements, stats, warnings = service.parse_document_pages(pages, file_name="filter_test.pdf")

    tags = [e.tag for e in elements]
    types = {e.element_type.upper() for e in elements}

    assert "AI1.1" in tags
    assert "DI8001.1" in tags
    assert "AO8002.1" in tags
    assert "PIDCON1" not in tags
    assert "AIC1" not in tags
    assert "DAT1" not in tags
    assert "MANSTN1" not in tags
    assert "TEXT1" not in tags
    assert types == {"AI", "DI800", "AO800"}


def test_underscore_800_series_detection_and_export():
    """
    Production DB listings use AI800_1.1 / AI800_1 AI810 notation.
    Cards must not export; channels must export as AI800/AO800/DI800/DO800.
    """
    pages = [
        {
            "page_number": 1,
            "text": """
AI800_1   AI810
  :ADDR 100
  :NAME   AI800_1

AI800_1.1
  :NAME "940LC391.MV"
  :UNIT "bar"

AI800_1.2
  :NAME "940LC392.MV"

AO800_3   AO810
  :ADDR 200

AO800_3.1
  :NAME "940FC400.OUT"

DI800_2   DI820
  :ADDR 300

DI800_2.1
  :NAME "100XV101.RUN"

DO800_2   DO820
  :ADDR 400

DO800_2.1
  :NAME "100XV101.OUT"

DO800_10.8
  :NAME "82M073.MSTR"
"""
        }
    ]

    service = ParserService("test_job_800_underscore")
    elements, stats, warnings = service.parse_document_pages(
        pages, file_name="underscore_800.pdf"
    )

    tags = {e.tag for e in elements}
    by_tag = {e.tag: e for e in elements}
    types = {e.element_type.upper() for e in elements}

    # Channels exported with underscore engineering references
    assert "AI800_1.1" in tags
    assert "AI800_1.2" in tags
    assert "AO800_3.1" in tags
    assert "DI800_2.1" in tags
    assert "DO800_2.1" in tags
    assert "DO800_10.8" in tags

    # Card definitions must NEVER be exported as signal rows
    assert "AI800_1" not in tags
    assert "AO800_3" not in tags
    assert "DI800_2" not in tags
    assert "DO800_2" not in tags

    assert types == {"AI800", "AO800", "DI800", "DO800"}
    assert by_tag["AI800_1.1"].element_type == "AI800"
    assert by_tag["AI800_1.1"].element_index == "1.1"
    assert by_tag["AI800_1.1"].get_parameter("NAME") == "940LC391.MV"
    # Card ADDR inherited onto channel
    assert by_tag["AI800_1.1"].get_parameter("ADDR") == 100
    assert by_tag["AO800_3.1"].get_parameter("ADDR") == 200

    from backend.mapper.record_clubber import RecordClubber
    from backend.mapper.element_mapper import ElementMapper
    from backend.mapper.output_formatter import OutputFormatter

    clubbed = RecordClubber("test_job_800_underscore").club_elements(elements)
    rows = OutputFormatter("test_job_800_underscore").format_clubbed_rows(
        ElementMapper("test_job_800_underscore").map_clubbed(clubbed)
    )
    assert sum(1 for r in rows if r.get("AI800_") == 1) == 2
    assert sum(1 for r in rows if r.get("AO800_") == 1) == 1
    assert sum(1 for r in rows if r.get("DI800_") == 1) == 1
    assert sum(1 for r in rows if r.get("DO800_") == 1) == 2
    # AI800→AO800 pairing by Loop Tag
    assert any(r.get("AI800_") == 1 and r["Loop Tag"] == "940LC391" for r in rows)
    assert any(r.get("AO800_") == 1 and r["Loop Tag"] == "940FC400" for r in rows)


def test_object_parser_recognizes_all_800_header_forms():
    from backend.parser.object_parser import ObjectParser

    p = ObjectParser("hdr")
    assert p.is_object_header("AI800_1.1") == ("AI800", "1.1", "AI800_1.1")
    assert p.is_object_header("DO800_10.8") == ("DO800", "10.8", "DO800_10.8")
    assert p.is_object_header("AI8001.1") == ("AI800", "1.1", "AI8001.1")
    assert p.is_object_header("AI800 1.1") == ("AI800", "1.1", "AI8001.1")
    assert p.is_object_header("AI 8001.1") == ("AI800", "1.1", "AI8001.1")
    assert p.is_object_header("AI1.4") == ("AI", "1.4", "AI1.4")


def test_card_parser_recognizes_underscore_800_cards():
    from backend.parser.card_parser import CardParser

    p = CardParser("card")
    assert p.is_card_header("AI800_1   AI810") == ("AI800_1", "AI800")
    assert p.is_card_header("AO800_3 AO810") == ("AO800_3", "AO800")
    assert p.is_card_header("DI800_2 DI820") == ("DI800_2", "DI800")
    assert p.is_card_header("DO800_10 DO820") == ("DO800_10", "DO800")
    assert p.is_card_header("AI8001 AI800") == ("AI8001", "AI800")
    assert p.is_card_header("AI1 AI") == ("AI1", "AI")
    # Must not treat channel objects as cards
    assert p.is_card_header("AI800_1.1") is None
