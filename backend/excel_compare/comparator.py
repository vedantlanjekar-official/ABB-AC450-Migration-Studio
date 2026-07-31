"""
comparator.py — Set-based engineering tag comparison (NOT row-by-row).

Matching:
  Excel 1 → ``$(DEVICETAG)`` values
  Excel 2 → ``$(DEVICETAG)`` values

Comparison is case-insensitive after trim (engineering tags), but each
tag is counted once. Row order is irrelevant and unmatched values from
both files retain their source workbook and worksheet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

from backend.excel_compare.column_extractor import (
    extract_engineering_device_tags_detailed,
    ExtractionResult,
)


@dataclass(frozen=True)
class UnmatchedTag:
    tag: str
    source_file: str
    source_sheet: str
    missing_from_file: str


@dataclass
class ComparisonResult:
    worksheet1_records: int = 0
    worksheet2_records: int = 0
    matched_records: int = 0
    unmatched_records: int = 0
    matched_tags: List[str] = field(default_factory=list)
    unmatched_tags: List[str] = field(default_factory=list)
    worksheet1_file: str = ""
    worksheet2_file: str = ""
    worksheet1_sheet: str = ""
    worksheet2_sheet: str = ""
    worksheet1_raw_rows: int = 0
    worksheet2_raw_rows: int = 0
    worksheet1_duplicates: int = 0
    worksheet2_duplicates: int = 0
    extra_in_worksheet2: List[str] = field(default_factory=list)
    unmatched_in_worksheet1: List[str] = field(default_factory=list)
    unmatched_in_worksheet2: List[str] = field(default_factory=list)
    unmatched_items: List[UnmatchedTag] = field(default_factory=list)

    def summary_lines(self) -> List[str]:
        return [
            f"Excel 1 Records : {self.worksheet1_records}",
            f"Excel 2 Records : {self.worksheet2_records}",
            f"Matched Records : {self.matched_records}",
            f"Total Unmatched Records : {self.unmatched_records}",
        ]


class ExcelComparator:
    """Symmetrically compare ``$(DEVICETAG)`` sets from any two workbooks."""

    def compare(
        self,
        worksheet1_path: Path | str,
        worksheet2_path: Path | str,
    ) -> ComparisonResult:
        path1 = Path(worksheet1_path)
        path2 = Path(worksheet2_path)

        ws1: ExtractionResult = extract_engineering_device_tags_detailed(path1)
        ws2: ExtractionResult = extract_engineering_device_tags_detailed(path2)

        # Case-insensitive set matching while preserving source spelling/order.
        worksheet1_lookup: Set[str] = {tag.upper() for tag in ws1.values}
        worksheet2_lookup: Set[str] = {tag.upper() for tag in ws2.values}

        matched = [
            tag for tag in ws1.values if tag.upper() in worksheet2_lookup
        ]
        only_in_worksheet1 = [
            tag for tag in ws1.values if tag.upper() not in worksheet2_lookup
        ]
        only_in_worksheet2 = [
            tag for tag in ws2.values if tag.upper() not in worksheet1_lookup
        ]
        unmatched_items = [
            UnmatchedTag(
                tag=tag,
                source_file=path1.name,
                source_sheet=ws1.sheet_name,
                missing_from_file=path2.name,
            )
            for tag in only_in_worksheet1
        ] + [
            UnmatchedTag(
                tag=tag,
                source_file=path2.name,
                source_sheet=ws2.sheet_name,
                missing_from_file=path1.name,
            )
            for tag in only_in_worksheet2
        ]

        return ComparisonResult(
            worksheet1_records=len(ws1.values),
            worksheet2_records=len(ws2.values),
            matched_records=len(matched),
            unmatched_records=len(unmatched_items),
            matched_tags=matched,
            unmatched_tags=[item.tag for item in unmatched_items],
            worksheet1_file=path1.name,
            worksheet2_file=path2.name,
            worksheet1_sheet=ws1.sheet_name,
            worksheet2_sheet=ws2.sheet_name,
            worksheet1_raw_rows=ws1.raw_row_count,
            worksheet2_raw_rows=ws2.raw_row_count,
            worksheet1_duplicates=ws1.duplicates_skipped,
            worksheet2_duplicates=ws2.duplicates_skipped,
            extra_in_worksheet2=only_in_worksheet2,
            unmatched_in_worksheet1=only_in_worksheet1,
            unmatched_in_worksheet2=only_in_worksheet2,
            unmatched_items=unmatched_items,
        )
