"""
parser_service.py - Production orchestrator for ABB AC450 PC Element extraction.

Pipeline:
  1. Multi-layer PDF read (+ optional OCR)
  2. Page cleaning
  3. Multi-strategy I/O detection (regex + spatial tokens + line stitching)
  4-5. Engineering grammar parse
  6. Description mapping (text + spatial)
  7-8. Metadata extraction
  9. Exact-duplicate removal
  10. Validation (invalid refs logged, not silently dropped without record)
  11. Completeness audit + validation report
  12. Loop Tag record clubbing (AI→AO, DO→DI, 800-series, valves)
  13. Output formatting (engineering section sequence)
  14. Excel generation (single consolidated worksheet)
"""

from typing import List, Dict, Any, Optional
import time
import os
import re
import logging
from pathlib import Path
from pydantic import BaseModel, Field

from backend.pc_element.parser.pdf_reader import PDFReader, PageContent
from backend.pc_element.parser.page_cleaner import PageCleaner
from backend.pc_element.parser.io_reference_detector import IOReferenceDetector
from backend.pc_element.parser.grammar_parser import GrammarParser, ParsedIOReference
from backend.pc_element.parser.metadata_extractor import MetadataExtractor, DocumentMetadata
from backend.pc_element.parser.description_mapper import DescriptionMapper
from backend.pc_element.parser.duplicate_detector import DuplicateDetector
from backend.pc_element.parser.validator import Validator, EngineeringIO
from backend.pc_element.parser.record_clubber import RecordClubber
from backend.pc_element.parser.output_formatter import OutputFormatter
from backend.pc_element.parser.category_mapper import apply_category_columns
from backend.pc_element.parser.excel_generator import ExcelGenerator
from backend.pc_element.parser.completeness_auditor import CompletenessAuditor

logger = logging.getLogger("pc_element_parser")


class PCParseResult(BaseModel):
    job_id: str
    total_pages_read: int = 0
    total_pages_processed: int = 0
    total_io_found: int = 0
    ai800_count: int = 0
    ao800_count: int = 0
    di800_count: int = 0
    do800_count: int = 0
    ai_count: int = 0
    ao_count: int = 0
    di_count: int = 0
    do_count: int = 0
    aoc_count: int = 0
    aic_count: int = 0
    other_count: int = 0
    successfully_parsed: int = 0
    invalid_references: int = 0
    duplicate_references: int = 0
    duplicates_removed: int = 0
    descriptions_found: int = 0
    descriptions_missing: int = 0
    inventory_detectable: int = 0
    parser_accuracy_percent: float = 0.0
    missing_from_inventory: int = 0
    controller_found: str = ""
    process_area_found: str = ""
    processing_time_seconds: float = 0.0
    excel_file_path: Optional[str] = None
    validation_report_path: Optional[str] = None
    validation_report: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    preview_data: List[Dict[str, Any]] = Field(default_factory=list)


class PCParserService:
    """Production pipeline orchestrator for PC Diagram hardwired I/O parsing."""

    def __init__(self, file_path: str, job_id: str, output_dir: str):
        self.file_path = file_path
        self.job_id = job_id
        self.output_dir = output_dir

    def execute_pipeline(self) -> PCParseResult:
        start_time = time.time()
        result = PCParseResult(job_id=self.job_id)

        try:
            logger.info(f"[{self.job_id}] Stage 1: Multi-layer PDF read...")
            reader = PDFReader(self.file_path)
            pages: List[PageContent] = reader.read_all_pages()

            result.total_pages_read = len(pages)
            result.total_pages_processed = len(pages)
            page_texts = [p.text for p in pages]
            pages_words = [p.words for p in pages]

            low_density_pages = sum(1 for p in pages if p.low_text_density)
            if low_density_pages:
                result.warnings.append(
                    f"{low_density_pages} page(s) had low selectable-text density; "
                    "OCR enrichment was attempted where available."
                )

            logger.info(f"[{self.job_id}] Stages 7-8: Title-block metadata...")
            metadata: DocumentMetadata = MetadataExtractor.extract_metadata_from_pages(page_texts)
            result.controller_found = metadata.controller
            result.process_area_found = metadata.process_area

            logger.info(f"[{self.job_id}] Stage 6: Description map (text + spatial)...")
            desc_map = DescriptionMapper.build_description_map(page_texts, pages_words)

            parsed_references: List[ParsedIOReference] = []
            skipped_candidates: List[str] = []

            for page in pages:
                cleaned_lines = PageCleaner.clean_page_lines(page.raw_lines)
                candidates = IOReferenceDetector.detect_candidates_in_page(
                    page.text,
                    cleaned_lines,
                    words=page.words,
                    text_layers=page.text_layers,
                )

                for cand in candidates:
                    refs = GrammarParser.parse_all_references(cand, page_number=page.page_number)
                    if refs:
                        parsed_references.extend(refs)
                    else:
                        # Keep an audit trail of candidates that looked like I/O but failed grammar
                        upper = cand.upper()
                        if "/" in cand and re.search(r'\b(?:AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)\b', upper):
                            skipped_candidates.append(cand[:120])

            logger.info(
                f"[{self.job_id}] Detected {len(parsed_references)} raw I/O matches; "
                f"{len(skipped_candidates)} non-parseable candidates logged."
            )

            unique_refs, dup_count = DuplicateDetector.deduplicate_references(parsed_references)
            result.duplicate_references = dup_count
            result.duplicates_removed = dup_count

            io_objects: List[EngineeringIO] = []
            for ref in unique_refs:
                page_idx = ref.page_number - 1
                page_text = page_texts[page_idx] if 0 <= page_idx < len(page_texts) else ""
                page_words = pages_words[page_idx] if 0 <= page_idx < len(pages_words) else None

                desc = DescriptionMapper.find_description_for_tag(
                    ref.loop_tag,
                    page_text,
                    desc_map,
                    page_words=page_words,
                )

                io_objects.append(
                    EngineeringIO(
                        io_family=ref.io_family,
                        io_type=ref.io_type,
                        category=ref.category,
                        card_number=ref.card_number,
                        channel_number=ref.channel_number,
                        loop_tag=ref.loop_tag,
                        device_tag=ref.device_tag,
                        description=desc,
                        controller=metadata.controller,
                        process_area=metadata.process_area,
                        page_number=ref.page_number,
                        source_reference=ref.source_reference,
                    )
                )

            valid_objects, validation_warnings = Validator.filter_and_validate_all(io_objects)
            result.warnings.extend(validation_warnings)
            result.invalid_references = len(io_objects) - len(valid_objects)

            result.total_io_found = len(valid_objects)
            result.successfully_parsed = len(valid_objects)

            for obj in valid_objects:
                f = obj.io_family.upper()
                if f == "AI800_":
                    result.ai800_count += 1
                elif f == "AO800_":
                    result.ao800_count += 1
                elif f == "DI800_":
                    result.di800_count += 1
                elif f == "DO800_":
                    result.do800_count += 1
                elif f == "AI":
                    result.ai_count += 1
                elif f == "AO":
                    result.ao_count += 1
                elif f == "DI":
                    result.di_count += 1
                elif f == "DO":
                    result.do_count += 1
                else:
                    result.other_count += 1

                if obj.description:
                    result.descriptions_found += 1
                else:
                    result.descriptions_missing += 1

            # Completeness audit + validation report
            report = CompletenessAuditor.audit(
                pages=pages,
                extracted=valid_objects,
                duplicates_removed=dup_count,
                invalid_count=result.invalid_references,
                skipped_candidates=skipped_candidates,
            )
            result.validation_report = report
            result.inventory_detectable = report.get("inventory_detectable_references", 0)
            result.parser_accuracy_percent = float(report.get("parser_accuracy_percent", 0))
            result.missing_from_inventory = int(report.get("missing_from_extraction", 0))
            for w in report.get("completeness_warnings") or []:
                result.warnings.append(w)

            report_path = CompletenessAuditor.write_report(report, self.output_dir, self.job_id)
            result.validation_report_path = report_path

            # Stage 12-13: Loop Tag clubbing + engineering presentation order
            # (mirrors DB Element RecordClubber + OutputFormatter)
            clubbed_objects = RecordClubber(self.job_id).club_elements(valid_objects)
            formatted_objects = OutputFormatter(self.job_id).format_clubbed_elements(
                clubbed_objects
            )
            logger.info(
                f"[{self.job_id}] VALIDATION raw_parsed={len(parsed_references)} "
                f"unique={len(unique_refs)} valid={len(valid_objects)} "
                f"clubbed={len(clubbed_objects)} exported={len(formatted_objects)} "
                f"dups={dup_count} invalid={result.invalid_references}"
            )

            from backend.utils.file_utils import pdf_to_excel_filename, unique_output_path

            export_name = pdf_to_excel_filename(Path(self.file_path).name)
            excel_path = str(unique_output_path(self.output_dir, export_name))
            ExcelGenerator.generate_excel(formatted_objects, excel_path)
            result.excel_file_path = excel_path

            preview_rows = []
            for sr, item in enumerate(formatted_objects[:150], start=1):
                preview_rows.append(apply_category_columns({
                    "Sr. No.": sr,
                    "Loop Tag": item.loop_tag,
                    "Description": item.description,
                    "Device Tag": item.device_tag,
                    "Category": item.category,
                    "Slot/Card": item.card_number,
                    "Channel": item.channel_number if item.channel_number > 0 else "",
                }))
            result.preview_data = preview_rows

            logger.info(
                f"[{self.job_id}] Done -> extracted={result.successfully_parsed}, "
                f"inventory={result.inventory_detectable}, "
                f"accuracy={result.parser_accuracy_percent}%, "
                f"missing={result.missing_from_inventory}, "
                f"dups={result.duplicates_removed}, invalid={result.invalid_references}"
            )

        except Exception as e:
            logger.error(f"[{self.job_id}] PC Element Pipeline error: {str(e)}", exc_info=True)
            result.errors.append(f"Pipeline error: {str(e)}")

        result.processing_time_seconds = round(time.time() - start_time, 2)
        return result
