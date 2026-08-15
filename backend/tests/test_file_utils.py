"""Tests for PDF → Excel export filename helpers."""

from pathlib import Path
from backend.utils.file_utils import (
    pdf_to_excel_filename,
    excel_filename_from_uploads,
    combined_export_filename,
    unique_output_path,
    sanitize_filename,
)


def test_pdf_to_excel_filename_preserves_base():
    assert pdf_to_excel_filename("DB_Element.pdf") == "DB_Element.xlsx"
    assert pdf_to_excel_filename("PB_Element.PDF") == "PB_Element.xlsx"
    assert pdf_to_excel_filename("Plant_Area_01.pdf") == "Plant_Area_01.xlsx"
    assert pdf_to_excel_filename("Unit-5_IO_List.pdf") == "Unit-5_IO_List.xlsx"
    assert pdf_to_excel_filename("940_Project.pdf") == "940_Project.xlsx"
    assert pdf_to_excel_filename("ABB Project 01.pdf") == "ABB Project 01.xlsx"
    assert pdf_to_excel_filename("24JA01.BAX") == "24JA01.xlsx"
    assert pdf_to_excel_filename("ND2201.bax") == "ND2201.xlsx"


def test_excel_filename_from_uploads_uses_first_pdf():
    assert excel_filename_from_uploads(["ABB_Project_01.pdf"]) == "ABB_Project_01.xlsx"
    assert (
        excel_filename_from_uploads(["part1.pdf", "part2.pdf"]) == "part1.xlsx"
    )


def test_excel_filename_from_uploads_uses_bax_when_no_pdf():
    assert excel_filename_from_uploads(["24JA01.BAX"]) == "24JA01.xlsx"
    assert excel_filename_from_uploads(["notes.xlsx", "ND2201.bax"]) == "ND2201.xlsx"
    assert excel_filename_from_uploads(["a.pdf", "b.bax"]) == "a.xlsx"


def test_excel_filename_from_uploads_uses_aax():
    assert excel_filename_from_uploads(["23JA1601.AAX"]) == "23JA1601.xlsx"
    assert excel_filename_from_uploads(["notes.xlsx", "PC10.aax"]) == "PC10.xlsx"


def test_combined_export_filename_uses_stable_name_for_multi_file():
    assert combined_export_filename(
        ["a.pdf"],
        suffixes=(".pdf", ".bax"),
        combined_name="DB_Element.xlsx",
        fallback="DB_Element.xlsx",
    ) == "a.xlsx"
    assert combined_export_filename(
        ["part1.pdf", "part2.bax"],
        suffixes=(".pdf", ".bax"),
        combined_name="DB_Element.xlsx",
        fallback="DB_Element.xlsx",
    ) == "DB_Element.xlsx"
    assert combined_export_filename(
        ["one.aax", "two.pdf"],
        suffixes=(".pdf", ".aax"),
        combined_name="PC_Element_IO_List.xlsx",
        fallback="PC_Element.xlsx",
    ) == "PC_Element_IO_List.xlsx"


def test_unique_output_path_adds_suffix_only_on_conflict(tmp_path):
    first = unique_output_path(tmp_path, "Plant_Area_01.xlsx")
    assert first.name == "Plant_Area_01.xlsx"
    first.write_text("a")

    second = unique_output_path(tmp_path, "Plant_Area_01.xlsx")
    assert second.name == "Plant_Area_01 (2).xlsx"
    second.write_text("b")

    third = unique_output_path(tmp_path, "Plant_Area_01.xlsx")
    assert third.name == "Plant_Area_01 (3).xlsx"


def test_sanitize_filename_preserves_spaces_and_case():
    assert sanitize_filename("ABB Project_01.pdf") == "ABB Project_01.pdf"
    assert sanitize_filename(r"C:\uploads\Unit-5_IO_List.pdf") == "Unit-5_IO_List.pdf"
