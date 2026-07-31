"""Tests for DB Element post-clubbing output formatting layer."""

from backend.models.db_element import DBElement
from backend.mapper.record_clubber import RecordClubber
from backend.mapper.element_mapper import ElementMapper
from backend.mapper.output_formatter import OutputFormatter
from backend.mapper.category_mapper import CATEGORY_INDICATOR_COLUMNS


def _elem(tag: str, etype: str, name: str, index: str = "1", descr: str = "") -> DBElement:
    params = {"NAME": name}
    if descr:
        params["DESCR"] = descr
    return DBElement(
        tag=tag,
        element_type=etype,
        element_index=index,
        parameters=params,
    )


def _active_category(row: dict) -> str:
    for col in CATEGORY_INDICATOR_COLUMNS:
        if row.get(col) == 1:
            return col.rstrip("_") if col.endswith("800_") else col
    return ""


def _pipeline(elements):
    clubbed = RecordClubber("test").club_elements(elements)
    rows = ElementMapper("test").map_clubbed(clubbed)
    return OutputFormatter("test").format_clubbed_rows(rows)


def test_formatter_engineering_section_sequence():
    """All AI–AO groups, then DO–DI, then 800-series — pairs stay adjacent."""
    elements = [
        _elem("DI8001.1", "DI800", "Z99.RUN", "9"),
        _elem("DO1.1", "DO", "940XV102.OUT", "8"),
        _elem("AI8001.1", "AI800", "C20.MV", "7"),
        _elem("AO2.1", "AO", "940LT210.OUT", "6"),
        _elem("AI1.1", "AI", "940FQ390.MV", "5"),
        _elem("AO1.1", "AO", "940FQ390.OUT", "4"),
        _elem("AI2.1", "AI", "940LT210.MV", "3"),
        _elem("DI1.1", "DI", "940XV101.RUN", "2"),
        _elem("DO2.1", "DO", "940XV101.OUT", "1"),
        _elem("AO8001.1", "AO800", "C20.OUT", "10"),
        _elem("DO8001.1", "DO800", "Z99.OUT", "11"),
        _elem("DI2.1", "DI", "940XV102.RUN", "12"),
    ]
    rows = _pipeline(elements)

    assert [_active_category(r) for r in rows] == [
        "AI", "AO",
        "AI", "AO",
        "DO", "DI",
        "DO", "DI",
        "AI800", "AO800",
        "DO800", "DI800",
    ]
    assert [r["NAME"] for r in rows] == [
        "940FQ390.MV", "940FQ390.OUT",
        "940LT210.MV", "940LT210.OUT",
        "940XV101.OUT", "940XV101.RUN",
        "940XV102.OUT", "940XV102.RUN",
        "C20.MV", "C20.OUT",
        "Z99.OUT", "Z99.RUN",
    ]
    assert "Category" not in rows[0]
    assert all(col in rows[0] for col in CATEGORY_INDICATOR_COLUMNS)


def test_formatter_preserves_original_index():
    """Index preserves original PDF index value after formatting; does not renumber 1..N."""
    elements = [
        _elem("AO2.1", "AO", "940FQ390.OUT", "99.9"),
        _elem("AI1.1", "AI", "940FQ390.MV", "0.1"),
        _elem("DI3.1", "DI", "940XV101.RUN", "50"),
        _elem("DO4.1", "DO", "940XV101.OUT", "7"),
    ]
    rows = _pipeline(elements)
    assert [r["Index"] for r in rows] == ["0.1", "99.9", "7", "50"]
    assert [_active_category(r) for r in rows] == ["AI", "AO", "DO", "DI"]


def test_formatter_preserves_pairs_when_input_jumbled():
    """Even if mapped rows arrive out of section order, pairs stay together and keep original Index."""
    jumbled = [
        {"Category": "DI", "Tag": "DI1.1", "Index": "1.1", "NAME": "940XV101.RUN", "Loop Tag": "940XV101"},
        {"Category": "AO", "Tag": "AO1.1", "Index": "2.2", "NAME": "940FQ390.OUT", "Loop Tag": "940FQ390"},
        {"Category": "DO", "Tag": "DO1.1", "Index": "3.3", "NAME": "940XV101.OUT", "Loop Tag": "940XV101"},
        {"Category": "AI", "Tag": "AI1.1", "Index": "4.4", "NAME": "940FQ390.MV", "Loop Tag": "940FQ390"},
        {"Category": "AI800", "Tag": "AI8001.1", "Index": "5.5", "NAME": "X.MV", "Loop Tag": "X"},
        {"Category": "AO800", "Tag": "AO8001.1", "Index": "6.6", "NAME": "X.OUT", "Loop Tag": "X"},
    ]
    rows = OutputFormatter("test").format_clubbed_rows(jumbled)
    assert [_active_category(r) for r in rows] == ["AI", "AO", "DO", "DI", "AI800", "AO800"]
    assert [r["Loop Tag"] for r in rows] == [
        "940FQ390", "940FQ390", "940XV101", "940XV101", "X", "X",
    ]
    assert [r["Index"] for r in rows] == ["4.4", "2.2", "3.3", "1.1", "5.5", "6.6"]


def test_formatter_does_not_invent_placeholders():
    rows = OutputFormatter("test").format_clubbed_rows([
        {"Category": "AI", "Tag": "AI1.1", "Index": "1.4", "NAME": "SOLO.MV", "Loop Tag": "SOLO"},
    ])
    assert len(rows) == 1
    assert rows[0]["AI"] == 1
    assert rows[0]["AO"] == ""
    assert "Category" not in rows[0]
    assert rows[0]["Index"] == "1.4"


def test_formatter_inserts_indicators_immediately_after_descr():
    """Eight category columns sit directly after DESCR; Category is removed."""
    rows = OutputFormatter("test").format_clubbed_rows([
        {
            "Category": "DI800",
            "Tag": "DI800_2.1",
            "Index": "2.1",
            "NAME": "940M02M1.RUN",
            "Loop Tag": "940M02M1",
            "DESCR": "Motor Running Status",
            "UNIT": "N/A",
            "TYPE": "DI",
        }
    ])
    keys = list(rows[0].keys())
    assert "Category" not in keys
    descr_idx = keys.index("DESCR")
    assert keys[descr_idx] == "DESCR"
    assert keys[descr_idx + 1: descr_idx + 9] == CATEGORY_INDICATOR_COLUMNS
    # Remaining columns keep original relative order after the indicators
    assert keys[descr_idx + 9:] == ["UNIT", "TYPE"]
    assert rows[0]["DI800_"] == 1
    assert rows[0]["AI"] == ""
    assert rows[0]["NAME"] == "940M02M1.RUN"
    assert rows[0]["DESCR"] == "Motor Running Status"


def test_formatter_always_places_indicators_after_descr_even_when_blank():
    """When DESCR is missing on the source row, a blank DESCR is created before indicators."""
    rows = OutputFormatter("test").format_clubbed_rows([
        {
            "Category": "AI",
            "Tag": "AI1.1",
            "Index": "1.1",
            "NAME": "940LC391.MV",
            "Loop Tag": "940LC391",
            "UNIT": "bar",
        }
    ])
    keys = list(rows[0].keys())
    assert "DESCR" in keys
    descr_idx = keys.index("DESCR")
    assert keys[descr_idx + 1: descr_idx + 9] == CATEGORY_INDICATOR_COLUMNS
    assert rows[0]["AI"] == 1
    assert rows[0]["DESCR"] == ""
    assert keys.index("Loop Tag") < descr_idx
    assert keys.index("UNIT") > descr_idx + 8
