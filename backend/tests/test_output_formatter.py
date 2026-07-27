"""Tests for DB Element post-clubbing output formatting layer."""

from backend.models.db_element import DBElement
from backend.mapper.record_clubber import RecordClubber
from backend.mapper.element_mapper import ElementMapper
from backend.mapper.output_formatter import OutputFormatter


def _elem(tag: str, etype: str, name: str, index: str = "1") -> DBElement:
    return DBElement(
        tag=tag,
        element_type=etype,
        element_index=index,
        parameters={"NAME": name},
    )


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

    assert [r["Category"] for r in rows] == [
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


def test_formatter_renumbers_index_sequentially():
    """Index becomes 1..N after formatting; does not keep engineering channel index."""
    elements = [
        _elem("AO2.1", "AO", "940FQ390.OUT", "99.9"),
        _elem("AI1.1", "AI", "940FQ390.MV", "0.1"),
        _elem("DI3.1", "DI", "940XV101.RUN", "50"),
        _elem("DO4.1", "DO", "940XV101.OUT", "7"),
    ]
    rows = _pipeline(elements)
    assert [r["Index"] for r in rows] == [1, 2, 3, 4]
    assert [r["Category"] for r in rows] == ["AI", "AO", "DO", "DI"]


def test_formatter_preserves_pairs_when_input_jumbled():
    """Even if mapped rows arrive out of section order, pairs stay together."""
    jumbled = [
        {"Category": "DI", "Tag": "DI1.1", "Index": "1", "NAME": "940XV101.RUN", "Loop Tag": "940XV101"},
        {"Category": "AO", "Tag": "AO1.1", "Index": "2", "NAME": "940FQ390.OUT", "Loop Tag": "940FQ390"},
        {"Category": "DO", "Tag": "DO1.1", "Index": "3", "NAME": "940XV101.OUT", "Loop Tag": "940XV101"},
        {"Category": "AI", "Tag": "AI1.1", "Index": "4", "NAME": "940FQ390.MV", "Loop Tag": "940FQ390"},
        {"Category": "AI800", "Tag": "AI8001.1", "Index": "5", "NAME": "X.MV", "Loop Tag": "X"},
        {"Category": "AO800", "Tag": "AO8001.1", "Index": "6", "NAME": "X.OUT", "Loop Tag": "X"},
    ]
    rows = OutputFormatter("test").format_clubbed_rows(jumbled)
    assert [r["Category"] for r in rows] == ["AI", "AO", "DO", "DI", "AI800", "AO800"]
    assert [r["Loop Tag"] for r in rows] == [
        "940FQ390", "940FQ390", "940XV101", "940XV101", "X", "X",
    ]
    assert [r["Index"] for r in rows] == [1, 2, 3, 4, 5, 6]


def test_formatter_does_not_invent_placeholders():
    rows = OutputFormatter("test").format_clubbed_rows([
        {"Category": "AI", "Tag": "AI1.1", "Index": "1", "NAME": "SOLO.MV", "Loop Tag": "SOLO"},
    ])
    assert len(rows) == 1
    assert rows[0]["Category"] == "AI"
    assert rows[0]["Index"] == 1
