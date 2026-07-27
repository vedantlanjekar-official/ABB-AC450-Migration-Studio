"""Tests for DB Element Loop Tag record clubbing."""

from backend.models.db_element import DBElement
from backend.mapper.record_clubber import (
    RecordClubber,
    derive_loop_tag,
    derive_name_suffix,
)
from backend.mapper.element_mapper import ElementMapper


def _elem(tag: str, etype: str, name: str, index: str = "1") -> DBElement:
    return DBElement(
        tag=tag,
        element_type=etype,
        element_index=index,
        parameters={"NAME": name},
    )


def test_derive_loop_tag_strips_final_suffix():
    assert derive_loop_tag("940FQ390.MV") == "940FQ390"
    assert derive_loop_tag("940FQ390.OUT") == "940FQ390"
    assert derive_loop_tag("940XV101.RUN") == "940XV101"
    assert derive_loop_tag("940XV101.SV1") == "940XV101"
    assert derive_loop_tag("949DKA050.KEY:SELECTED") == "949DKA050"
    assert derive_loop_tag("BOILER_PRESS_TR_01") == "BOILER_PRESS_TR_01"
    assert derive_loop_tag("") == ""


def test_derive_name_suffix():
    assert derive_name_suffix("940FQ390.MV") == "MV"
    assert derive_name_suffix("940XV101.SV1") == "SV1"
    assert derive_name_suffix("940XV101.GSO") == "GSO"
    assert derive_name_suffix("NO_SUFFIX") == ""


def test_ai_ao_clubbing_order():
    """AI → AO for the same Loop Tag; unpaired AI kept without placeholder."""
    elements = [
        _elem("AO2.1", "AO", "940FQ390.OUT", "2.1"),
        _elem("AI1.1", "AI", "940FQ390.MV", "1.1"),
        _elem("AI3.1", "AI", "941TI100.MV", "3.1"),  # unpaired AI
        _elem("AO9.1", "AO", "ZZZ999.OUT", "9.1"),   # different loop
    ]
    clubbed = RecordClubber("test").club_elements(elements)
    names = [e.get_parameter("NAME") for e in clubbed]

    # Within AI–AO section, Loop Tags alphabetical: 940FQ390, 941TI100, ZZZ999
    assert names[0] == "940FQ390.MV"
    assert names[1] == "940FQ390.OUT"
    assert names[2] == "941TI100.MV"
    assert names[3] == "ZZZ999.OUT"
    assert len(clubbed) == 4  # no empty AO placeholder for unpaired AI


def test_do_di_clubbing_order():
    """DO → DI for the same Loop Tag."""
    elements = [
        _elem("DI1.1", "DI", "940XV101.RUN", "1.1"),
        _elem("DO2.1", "DO", "940XV101.OUT", "2.1"),
    ]
    clubbed = RecordClubber("test").club_elements(elements)
    assert [e.element_type for e in clubbed] == ["DO", "DI"]
    assert [e.get_parameter("NAME") for e in clubbed] == [
        "940XV101.OUT",
        "940XV101.RUN",
    ]


def test_family_sections_ai_ao_before_do_di():
    """All AI–AO clubs complete before any DO–DI, even if digital Loop Tag sorts first."""
    elements = [
        _elem("DI1.1", "DI", "100XV001.RUN"),
        _elem("DO1.1", "DO", "100XV001.OUT"),
        _elem("AO2.1", "AO", "940FQ390.OUT"),
        _elem("AI2.1", "AI", "940FQ390.MV"),
    ]
    clubbed = RecordClubber("test").club_elements(elements)
    assert [e.element_type for e in clubbed] == ["AI", "AO", "DO", "DI"]
    assert [e.get_parameter("NAME") for e in clubbed] == [
        "940FQ390.MV",
        "940FQ390.OUT",
        "100XV001.OUT",
        "100XV001.RUN",
    ]


def test_ai800_ao800_and_do800_di800_section_order():
    """AI800–AO800 section before DO800–DI800 section."""
    elements = [
        _elem("DI8001.1", "DI800", "100XV101.RUN"),
        _elem("DO8001.1", "DO800", "100XV101.OUT"),
        _elem("AO8001.1", "AO800", "940FQ390.OUT"),
        _elem("AI8001.1", "AI800", "940FQ390.MV"),
    ]
    clubbed = RecordClubber("test").club_elements(elements)
    assert [e.element_type for e in clubbed] == ["AI800", "AO800", "DO800", "DI800"]


def test_full_section_sequence():
    """Global order: AI–AO → DO–DI → AI800–AO800 → DO800–DI800."""
    elements = [
        _elem("DI8001.1", "DI800", "Z99.RUN"),
        _elem("DO1.1", "DO", "B10.OUT"),
        _elem("AI8001.1", "AI800", "C20.MV"),
        _elem("AI1.1", "AI", "A01.MV"),
        _elem("AO1.1", "AO", "A01.OUT"),
        _elem("DI1.1", "DI", "B10.RUN"),
        _elem("AO8001.1", "AO800", "C20.OUT"),
        _elem("DO8001.1", "DO800", "Z99.OUT"),
    ]
    clubbed = RecordClubber("test").club_elements(elements)
    assert [e.element_type for e in clubbed] == [
        "AI", "AO",
        "DO", "DI",
        "AI800", "AO800",
        "DO800", "DI800",
    ]


def test_valve_suffix_order_sv1_gso_gsc():
    elements = [
        _elem("DI1.3", "DI", "940XV200.GSC"),
        _elem("DO1.1", "DO", "940XV200.SV1"),
        _elem("DO1.2", "DO", "940XV200.GSO"),
    ]
    clubbed = RecordClubber("test").club_elements(elements)
    assert [e.get_parameter("NAME") for e in clubbed] == [
        "940XV200.SV1",
        "940XV200.GSO",
        "940XV200.GSC",
    ]


def test_single_worksheet_map_clubbed_adjacent_pairs():
    elements = [
        _elem("AO2.1", "AO", "940FQ390.OUT", "2.1"),
        _elem("AI1.1", "AI", "940FQ390.MV", "1.1"),
        _elem("DI3.1", "DI", "940XV101.RUN", "3.1"),
        _elem("DO4.1", "DO", "940XV101.OUT", "4.1"),
    ]
    clubber = RecordClubber("test")
    clubbed = clubber.club_elements(elements)
    rows = ElementMapper("test").map_clubbed(clubbed)

    assert [r["Category"] for r in rows] == ["AI", "AO", "DO", "DI"]
    assert [r["Loop Tag"] for r in rows] == [
        "940FQ390", "940FQ390", "940XV101", "940XV101",
    ]
    assert rows[0]["NAME"] == "940FQ390.MV"
    assert rows[1]["NAME"] == "940FQ390.OUT"
    assert rows[2]["NAME"] == "940XV101.OUT"
    assert rows[3]["NAME"] == "940XV101.RUN"
