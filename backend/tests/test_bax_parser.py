"""BAX DB Element reader + shared AST pipeline tests."""

from pathlib import Path

import pytest

from backend.mapper.element_mapper import ElementMapper
from backend.mapper.output_formatter import OutputFormatter
from backend.mapper.record_clubber import RecordClubber
from backend.parser.bax_reader import BaxReader
from backend.parser.parser_service import ParserService

SAMPLE_BAX_DIR = Path(r"c:\Users\admin\Downloads\PM2MP2\DBDATA")
FIXTURE_BAX = Path(__file__).resolve().parent / "fixtures" / "sample_db.bax"


def _write_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """(* sample BAX generated for unit tests *)
BEGIN DB
HEADER
BEGIN GENERAL DEFAULTS
DEFAULT AI
   :SERVICE              1
   :TYPE                 DSAI_130
   :SCANT                NOT USED

DEFAULT AIS
   :UNIT                 %
   :DEC                  2
   :DESCR

DEFAULT AO
   :SERVICE              1
   :TYPE                 DSAO_110

DEFAULT AOS
   :DEC                  1
   :UNIT                 %

DEFAULT DI
   :SERVICE              1
   :TYPE                 DSDI_110

DEFAULT DIS
   :DESCR

DEFAULT DO
   :SERVICE              1
   :TYPE                 DSDO_110

DEFAULT DOS
   :DESCR

END GENERAL DEFAULTS

AI1                   AI
   :ADDR                 32
   :TYPE                 DSAI_110
   :CONV_PAR             4..20mA

AI1.1              (* AIS *)
   :NAME                 82M001.IT
   :DESCR                DC Motor Cooling Fan
   :UNIT                 A
   :RANGEMAX             6.000000E+01

AI1.2              (* AIS *)
   :NAME                 82M007.IT
   :DESCR                No.2 Nash Vacuum

AO1                   AO
   :ADDR                 40

AO1.1              (* AOS *)
   :NAME                 82CV001.OUT
   :DESCR                Control Output

DI1                   DI
   :ADDR                 16

DI1.1              (* DIS *)
   :NAME                 82XS001.DI
   :DESCR                Limit Switch

DO1                   DO
   :ADDR                 24

DO1.1              (* DOS *)
   :NAME                 82YV001.DO
   :DESCR                Solenoid

PIDCON1               PIDCON
   :NAME                 SKIP_ME

END DB
""",
        encoding="utf-8",
    )


@pytest.fixture(scope="module", autouse=True)
def ensure_fixture():
    if not FIXTURE_BAX.exists():
        _write_fixture(FIXTURE_BAX)


def test_bax_reader_extracts_engineering_lines():
    records = BaxReader("test_bax").extract_line_records(FIXTURE_BAX)
    texts = [r.text for r in records]
    assert any(t.startswith("DEFAULT AI") for t in texts)
    assert any(t.startswith("AI1.1") for t in texts)
    assert not any(t.upper().startswith("BEGIN ") for t in texts)
    assert not any(t.startswith("(*") and t.endswith("*)") for t in texts)


def test_bax_fixture_feeds_shared_db_pipeline():
    reader = BaxReader("test_bax_pipe")
    records = reader.extract_line_records(FIXTURE_BAX)
    elements, stats, warnings = ParserService("test_bax_pipe").parse_line_records(
        records, file_name=FIXTURE_BAX.name
    )

    tags = {e.tag for e in elements}
    types = {e.element_type.upper() for e in elements}
    assert "AI1.1" in tags
    assert "AO1.1" in tags
    assert "DI1.1" in tags
    assert "DO1.1" in tags
    assert "PIDCON1" not in tags
    assert types == {"AI", "AO", "DI", "DO"}
    assert stats.hardware_default_blocks >= 2
    assert stats.software_default_blocks >= 2

    ai = next(e for e in elements if e.tag == "AI1.1")
    assert ai.get_parameter("NAME") == "82M001.IT"
    assert ai.get_parameter("TYPE") == "DSAI_110"  # card override over hardware default
    assert ai.get_parameter("DEC") == 2  # inherited from DEFAULT AIS
    assert ai.get_parameter("ADDR") == 32  # inherited from card AI1

    clubbed = RecordClubber("test_bax_pipe").club_elements(elements)
    rows = ElementMapper("test_bax_pipe").map_clubbed(clubbed)
    assert rows
    assert all("Category" in r for r in rows)
    categories = {r["Category"] for r in rows}
    assert categories.issubset({"AI", "AO", "DI", "DO", "AI800", "AO800", "DI800", "DO800"})

    formatted = OutputFormatter("test_bax_pipe").format_clubbed_rows(rows)
    assert formatted
    assert "Category" not in formatted[0]  # expanded into indicator columns
    assert any(r.get("AI") == 1 for r in formatted)
    assert any(r.get("AO") == 1 for r in formatted)


@pytest.mark.parametrize(
    "filename,expected_min",
    [
        ("24JA01.BAX", 400),
        ("ND2201.BAX", 400),
    ],
)
def test_sample_bax_files_parse_supported_io(filename: str, expected_min: int):
    path = SAMPLE_BAX_DIR / filename
    if not path.exists():
        pytest.skip(f"Sample BAX not available: {path}")

    records = BaxReader("sample_bax").extract_line_records(path)
    assert len(records) > 1000

    elements, stats, warnings = ParserService("sample_bax").parse_line_records(
        records, file_name=filename
    )
    assert len(elements) >= expected_min
    types = {e.element_type.upper() for e in elements}
    assert types.issubset({"AI", "AO", "DI", "DO", "AI800", "AO800", "DI800", "DO800"})
    assert "AI1.1" in {e.tag for e in elements}
    assert stats.inherited_parameters > 0

    ai1_1 = next(e for e in elements if e.tag == "AI1.1")
    assert ai1_1.get_parameter("NAME")
    assert ai1_1.get_parameter("DESCR")
