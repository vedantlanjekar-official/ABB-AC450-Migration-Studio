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
from backend.pc_element.parser.io_reference_detector import IOReferenceDetector


def test_user_examples_extraction():
    """Test all explicit user example formats from the request prompt."""

    ref1 = GrammarParser.parse_reference("=AI1.1/940LC391.MV")
    assert ref1 is not None
    assert ref1.category == "AI"
    assert ref1.card_number == 1
    assert ref1.channel_number == 1
    assert ref1.loop_tag == "940LC391"
    assert ref1.device_tag == "940LC391.MV"

    ref2 = GrammarParser.parse_reference("=AO2.3/945FC400.OUT")
    assert ref2 is not None
    assert ref2.category == "AO"
    assert ref2.device_tag == "945FC400.OUT"

    ref3 = GrammarParser.parse_reference("=DI5.12/940M03M1.RUN")
    assert ref3 is not None
    assert ref3.category == "DI"

    ref4 = GrammarParser.parse_reference("=DO8.6/946M22M2.STOP")
    assert ref4 is not None
    assert ref4.category == "DO"

    ref5 = GrammarParser.parse_reference("=AI800_1.1/940LC391.MV")
    assert ref5 is not None
    assert ref5.category == "AI800"
    assert ref5.io_family == "AI800_"
    assert ref5.loop_tag == "940LC391"
    assert ref5.device_tag == "940LC391.MV"

    ref6 = GrammarParser.parse_reference("DO800_1.16/82M073.MSTR")
    assert ref6 is not None
    assert ref6.category == "DO800"
    assert ref6.io_type == "DO"

    ref7 = GrammarParser.parse_reference("-AI800_2.1/M49M021.CURR")
    assert ref7 is not None
    assert ref7.device_tag == "M49M021.CURR"
    assert ref7.loop_tag == "M49M021"


def test_channel_port_err_format():
    """CARD.CHANNEL:TERMINAL/TAG:ERR format from O2-PC32 page 8/34."""
    r = GrammarParser.parse_reference("=AI800_22.5:22/M49FI1201.MV:ERR")
    assert r is not None
    assert r.category == "AI800"
    assert r.card_number == 22
    assert r.channel_number == 5
    assert r.device_tag == "M49FI1201.MV:ERR"
    assert r.loop_tag == "M49FI1201"

    r2 = GrammarParser.parse_reference("=AI800_2.1:22/M49M021.CURR:ERR")
    assert r2 is not None
    assert r2.card_number == 2
    assert r2.channel_number == 1
    assert r2.device_tag == "M49M021.CURR:ERR"
    assert r2.loop_tag == "M49M021"


def test_mv_and_err_are_distinct_rows():
    refs = [
        GrammarParser.parse_reference("=AI800_22.5/M49FI1201.MV"),
        GrammarParser.parse_reference("=AI800_22.5:22/M49FI1201.MV:ERR"),
    ]
    unique, dups = DuplicateDetector.deduplicate_references(refs)
    assert len(unique) == 2
    assert dups == 0


def test_complete_device_tag_keeps_attributes():
    """Complete device tags retain :ATTR suffixes; loop tag drops only the extension."""
    r = GrammarParser.parse_reference("=AI800_22.5:22/M49FI1201.MV:ERR")
    assert r is not None
    assert r.device_tag == "M49FI1201.MV:ERR"
    assert r.loop_tag == "M49FI1201"
    assert r.card_number == 22
    assert r.channel_number == 5

    r2 = GrammarParser.parse_reference("P-=AO2.3/M49DKA050.KEY:MAN")
    assert r2 is not None
    assert r2.device_tag == "M49DKA050.KEY:MAN"
    assert r2.loop_tag == "M49DKA050"
    assert r2.category == "AO"

    r3 = GrammarParser.parse_reference("=DI5.12/M49KN050.PWR:CALC_VAL")
    assert r3 is not None
    assert r3.device_tag == "M49KN050.PWR:CALC_VAL"
    assert r3.loop_tag == "M49KN050"
    assert r3.category == "DI"


def test_unsupported_categories_are_ignored():
    """AIC/AOC/DIC/DOC and other non-I/O families must not be parsed."""
    for ref in (
        "=AOC264:17/949DKA050.KEY:SELECTED",
        "=AIC793:55/M49KN050.PWR:CALC_VAL",
        "=DOC10:1/TAG.OUT",
        "=DIC5:2/TAG.IN",
        "=ACC1/TAG.X",
        "=AICT1.1/TAG.MV",
    ):
        assert GrammarParser.parse_reference(ref) is None


def test_dedup_keeps_all_address_variants():
    """MV / MV:ERR are distinct engineering references."""
    refs = [
        GrammarParser.parse_reference("=AI800_22.5/M49FI1201.MV"),
        GrammarParser.parse_reference("=AI800_22.5:22/M49FI1201.MV:ERR"),
        GrammarParser.parse_reference("=AO2.3/945FC400.OUT"),
    ]
    assert all(r is not None for r in refs)
    unique, dups = DuplicateDetector.deduplicate_references(refs)
    assert len(unique) == 3
    assert dups == 0
    tags = {r.device_tag for r in unique}
    assert tags == {"M49FI1201.MV", "M49FI1201.MV:ERR", "945FC400.OUT"}


def test_dedup_removes_exact_duplicates_only():
    refs = [
        GrammarParser.parse_reference("=AI1.1/940LC391.MV"),
        GrammarParser.parse_reference("=AI1.1/940LC391.MV"),
    ]
    unique, dups = DuplicateDetector.deduplicate_references(refs)
    assert len(unique) == 1
    assert dups == 1


def test_validator_rejects_unsupported_categories():
    obj = EngineeringIO(
        io_family="AOC",
        io_type="AOC",
        category="AOC",
        card_number=264,
        channel_number=0,
        loop_tag="949DKA050",
        device_tag="949DKA050.KEY",
        source_reference="=AOC264/949DKA050.KEY",
    )
    ok, errors = Validator.validate_object(obj)
    assert not ok
    assert any("category" in e.lower() or "family" in e.lower() for e in errors)


def test_validator_accepts_supported_zero_channel():
    obj = EngineeringIO(
        io_family="AO",
        io_type="AO",
        category="AO",
        card_number=199,
        channel_number=0,
        loop_tag="M49ARA104",
        device_tag="M49ARA104.CA41",
        source_reference="=AO199/M49ARA104.CA41",
    )
    ok, errors = Validator.validate_object(obj)
    assert ok, errors


def test_excel_generation_columns(tmp_path):
    obj1 = EngineeringIO(
        io_family="AI800_",
        io_type="AI",
        category="AI800",
        card_number=5,
        channel_number=10,
        loop_tag="82LIC660",
        device_tag="82LIC660.MV",
        description="Felt Water Tank",
    )
    obj2 = EngineeringIO(
        io_family="AO",
        io_type="AO",
        category="AO",
        card_number=2,
        channel_number=3,
        loop_tag="945FC400",
        device_tag="945FC400.OUT",
        description="",
    )

    out_file = str(tmp_path / "test_io_list.xlsx")
    ExcelGenerator.generate_excel([obj1, obj2], out_file)
    wb = openpyxl.load_workbook(out_file)
    ws = wb["I_O_List"]

    headers = [ws.cell(row=4, column=c).value for c in range(1, 8)]
    assert headers == [
        "Sr. No.", "Loop Tag", "Description", "Device Tag",
        "Category", "Slot/Card", "Channel",
    ]

    row5 = [ws.cell(row=5, column=c).value for c in range(1, 8)]
    assert row5[1] == "82LIC660"
    assert row5[3] == "82LIC660.MV"
    assert row5[4] == "AI800"
    assert row5[5] == 5
    assert row5[6] == 10


def test_pc_element_parser_service_pipeline(tmp_path):
    from unittest.mock import patch
    from backend.pc_element.parser.parser_service import PCParserService
    from backend.pc_element.parser.pdf_reader import PageContent

    mock_pages = [
        PageContent(
            page_number=1,
            text=(
                "-AI800_2.1/M49M021.CURR\n"
                "=AO2.3/945FC400.OUT\n"
                "=DI5.12/940M03M1.RUN\n"
                "=AOC264:17/949DKA050.KEY:SELECTED\n"
                "=AIC793:55/M49KN050.PWR:CALC_VAL\n"
                "Felt Water Tank Level\n"
                "PM2\\Node22\n"
                "White Water System"
            ),
            raw_lines=[
                "-AI800_2.1/M49M021.CURR",
                "=AO2.3/945FC400.OUT",
                "=DI5.12/940M03M1.RUN",
                "=AOC264:17/949DKA050.KEY:SELECTED",
                "=AIC793:55/M49KN050.PWR:CALC_VAL",
                "Felt Water Tank Level",
                "PM2\\Node22",
                "White Water System",
            ]
        )
    ]

    with patch(
        "backend.pc_element.parser.parser_service.PDFReader.read_all_pages",
        return_value=mock_pages,
    ):
        service = PCParserService(
            file_path=__file__,
            job_id="test_job",
            output_dir=str(tmp_path),
        )
        res = service.execute_pipeline()

        assert len(res.errors) == 0
        assert res.total_io_found == 3  # AI800 + AO + DI; AOC/AIC skipped
        assert res.ai800_count == 1
        assert res.ao_count == 1
        assert res.di_count == 1
        assert res.aoc_count == 0
        assert res.aic_count == 0
        cats = {row["Category"] for row in res.preview_data}
        assert cats == {"AI800", "AO", "DI"}
        assert set(res.preview_data[0].keys()) >= {
            "Sr. No.", "Loop Tag", "Description", "Device Tag",
            "Category", "Slot/Card", "Channel",
        }


@pytest.mark.integration
def test_reference_o2_pc32_full_coverage():
    """Every detectable I/O address in the user reference O2-PC32.pdf must be extracted."""
    import re
    import tempfile
    from backend.pc_element.parser.parser_service import PCParserService
    from backend.pc_element.parser.pdf_reader import PDFReader
    from backend.pc_element.parser.page_cleaner import PageCleaner
    from backend.pc_element.parser.io_reference_detector import IOReferenceDetector
    from backend.pc_element.parser.grammar_parser import GrammarParser
    from backend.pc_element.parser.duplicate_detector import DuplicateDetector
    from backend.pc_element.parser.validator import Validator, EngineeringIO

    pdf = r"c:\Users\vedan\Downloads\Testing Material\Project references\O2_LOGIC_PDF\O2-PC32.pdf"
    if not os.path.exists(pdf):
        pdf = r"backend\temp\uploads\0eb5589f-fbdf-4859-ad0b-edc9539aa4ec\O2-PC32.pdf"
    if not os.path.exists(pdf):
        pytest.skip("O2-PC32.pdf not available")

    # Include CARD.CHANNEL:TERMINAL/TAG form in ground truth — only 8 supported families
    STRICT = re.compile(
        r'''(?ix)
        (?:[-+]?\s*P\s*-?\s*=?\s*|[=+\-]+\s*)?
        (?P<prefix>AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)
        \s*_?\s*(?P<card>\d{1,4})
        (?:
            \s*\.\s*(?P<channel>\d{1,3})\s*:\s*(?P<terminal>\d{1,4})
          | \s*\.\s*(?P<channel2>\d{1,3})
          | \s*:\s*(?P<port>\d{1,4})
        )?
        \s*/\s*
        (?P<tag>[A-Za-z0-9_][A-Za-z0-9_\-]*(?:\.[A-Za-z0-9_]+)?(?::[A-Za-z0-9_]+)?)
        (?![A-Za-z0-9_.])
        '''
    )

    pages = PDFReader(pdf).read_all_pages()
    gt = set()
    for page in pages:
        for src in [page.text] + page.raw_lines:
            for m in STRICT.finditer(src or ""):
                prefix = m.group("prefix").upper()
                if prefix in ("AI800", "AO800", "DI800", "DO800"):
                    prefix = prefix + "_"
                card = int(m.group("card"))
                ch = m.group("channel") or m.group("channel2") or m.group("port")
                channel = int(ch) if ch else 0
                tag = m.group("tag").upper()
                gt.add((prefix, card, channel, tag))

    out = tempfile.mkdtemp()
    res = PCParserService(pdf, "cov_ref", out).execute_pipeline()
    assert not res.errors

    parsed = []
    for page in pages:
        cleaned = PageCleaner.clean_page_lines(page.raw_lines)
        for c in IOReferenceDetector.detect_candidates_in_page(page.text, cleaned):
            ref = GrammarParser.parse_reference(c, page.page_number)
            if ref:
                parsed.append(ref)
    unique, _ = DuplicateDetector.deduplicate_references(parsed)
    objs = [
        EngineeringIO(
            io_family=r.io_family, io_type=r.io_type, category=r.category,
            card_number=r.card_number, channel_number=r.channel_number,
            loop_tag=r.loop_tag, device_tag=r.device_tag,
            source_reference=r.source_reference, page_number=r.page_number,
        )
        for r in unique
    ]
    valid, _ = Validator.filter_and_validate_all(objs)
    out_keys = {
        (v.io_family.upper(), v.card_number, v.channel_number, v.device_tag.upper())
        for v in valid
    }

    missing = sorted(gt - out_keys)
    assert len(missing) == 0, f"Missing {len(missing)} refs, e.g. {missing[:15]}"
    assert res.total_io_found >= len(gt)
    # Must include the previously-missed ERR variants
    err_tags = {k for k in out_keys if k[3].endswith(":ERR")}
    assert len(err_tags) >= 15, f"Expected >=15 :ERR tags, got {len(err_tags)}"
