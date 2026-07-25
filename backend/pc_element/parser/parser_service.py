"""
parser_service.py - Orchestrator Service for ABB AC450 800-Series PC Element Extraction Engine.
"""

from typing import List, Dict, Any, Optional
import time
import os
import logging
from pydantic import BaseModel, Field

from backend.pc_element.parser.pdf_reader import PDFReader, PageContent
from backend.pc_element.parser.page_cleaner import PageCleaner
from backend.pc_element.parser.io_reference_detector import IOReferenceDetector
from backend.pc_element.parser.grammar_parser import GrammarParser, ParsedIOReference
from backend.pc_element.parser.metadata_extractor import MetadataExtractor, DocumentMetadata
from backend.pc_element.parser.description_mapper import DescriptionMapper
from backend.pc_element.parser.duplicate_detector import DuplicateDetector
from backend.pc_element.parser.validator import Validator, EngineeringIO
from backend.pc_element.parser.excel_generator import ExcelGenerator

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
    successfully_parsed: int = 0
    invalid_references: int = 0
    duplicate_references: int = 0
    duplicates_removed: int = 0
    descriptions_found: int = 0
    descriptions_missing: int = 0
    controller_found: str = ""
    process_area_found: str = ""
    processing_time_seconds: float = 0.0
    excel_file_path: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    preview_data: List[Dict[str, Any]] = Field(default_factory=list)


class PCParserService:
    """Pipeline Orchestrator Service for 800-Series PC Diagram Hardwired I/O Parsing."""

    def __init__(self, file_path: str, job_id: str, output_dir: str):
        self.file_path = file_path
        self.job_id = job_id
        self.output_dir = output_dir

    def execute_pipeline(self) -> PCParseResult:
        """Executes the pipeline stages sequentially."""
        start_time = time.time()
        result = PCParseResult(job_id=self.job_id)

        try:
            logger.info(f"[{self.job_id}] Stage 1: Reading PDF file...")
            reader = PDFReader(self.file_path)
            pages: List[PageContent] = reader.read_all_pages()

            result.total_pages_read = len(pages)
            result.total_pages_processed = len(pages)
            page_texts = [p.text for p in pages]

            logger.info(f"[{self.job_id}] Stage 2, 7 & 8: Extracting title block metadata...")
            metadata: DocumentMetadata = MetadataExtractor.extract_metadata_from_pages(page_texts)
            result.controller_found = metadata.controller
            result.process_area_found = metadata.process_area

            logger.info(f"[{self.job_id}] Stage 6: Building tag description map...")
            desc_map = DescriptionMapper.build_description_map(page_texts)

            parsed_references: List[ParsedIOReference] = []

            for page in pages:
                cleaned_lines = PageCleaner.clean_page_lines(page.raw_lines)
                candidates = IOReferenceDetector.detect_candidates_in_page(page.text, cleaned_lines)

                for cand in candidates:
                    ref = GrammarParser.parse_reference(cand, page_number=page.page_number)
                    if ref:
                        parsed_references.append(ref)

            logger.info(f"[{self.job_id}] Detected {len(parsed_references)} raw I/O reference matches.")

            # Stage 9: Deduplication
            unique_refs, dup_count = DuplicateDetector.deduplicate_references(parsed_references)
            result.duplicate_references = dup_count
            result.duplicates_removed = dup_count

            # Stage 6 & 10: Building EngineeringIO objects & validation
            io_objects: List[EngineeringIO] = []
            for ref in unique_refs:
                desc = DescriptionMapper.find_description_for_tag(
                    ref.loop_tag,
                    page_texts[ref.page_number - 1] if ref.page_number <= len(page_texts) else "",
                    desc_map
                )

                eng_io = EngineeringIO(
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
                    source_reference=ref.source_reference
                )
                io_objects.append(eng_io)

            # Validate objects
            valid_objects, validation_warnings = Validator.filter_and_validate_all(io_objects)
            result.warnings.extend(validation_warnings)
            result.invalid_references = len(io_objects) - len(valid_objects)

            result.total_io_found = len(valid_objects)
            result.successfully_parsed = len(valid_objects)

            # Metrics calculation for 800-Series and Standard Series
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

                if obj.description:
                    result.descriptions_found += 1
                else:
                    result.descriptions_missing += 1

            # Stage 11: Generate Excel Workbook
            excel_filename = f"PC_800_Series_IO_List_{self.job_id}.xlsx"
            excel_path = os.path.join(self.output_dir, excel_filename)
            ExcelGenerator.generate_excel(valid_objects, excel_path)
            result.excel_file_path = excel_path

            # Prepare preview rows matching Excel output format:
            # Sr No | Loop Tag | Description | Device Tag | IO Family | Card Number | Channel Number
            preview_rows = []
            for sr, item in enumerate(valid_objects[:100], start=1):
                preview_rows.append({
                    "Loop Tag": item.loop_tag,
                    "Tag Description": item.description,
                    "Device Tag": item.device_tag,
                    "IO type": item.io_type,
                    "Controller": item.controller,
                    "Process area": item.process_area
                })
            result.preview_data = preview_rows

            logger.info(
                f"[{self.job_id}] Parsing Stats -> Parsed: {result.successfully_parsed}, "
                f"AI800_: {result.ai800_count}, AO800_: {result.ao800_count}, "
                f"DI800_: {result.di800_count}, DO800_: {result.do800_count}, "
                f"Duplicates: {result.duplicate_references}, Invalid: {result.invalid_references}"
            )

        except Exception as e:
            logger.error(f"[{self.job_id}] 800-Series PC Element Pipeline error: {str(e)}", exc_info=True)
            result.errors.append(f"Pipeline error: {str(e)}")

        result.processing_time_seconds = round(time.time() - start_time, 2)
        return result
