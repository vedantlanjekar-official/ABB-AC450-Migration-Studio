import time
from pathlib import Path
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
from backend.models.pc_element import PCElement
from backend.pc_parser.pdf_reader import PCPDFReader, PCLineRecord
from backend.pc_parser.cleaner import PCDocumentCleaner
from backend.pc_parser.reference_detector import PCReferenceDetector
from backend.pc_parser.description_mapper import PCDescriptionMapper
from backend.pc_parser.validator import PCElementValidator
from backend.pc_parser.duplicate_checker import PCDuplicateChecker
from backend.pc_parser.excel_generator import PCExcelGenerator
from backend.core.logging import get_logger

@dataclass
class PCAuditStatistics:
    pages_read: int = 0
    headers_removed: int = 0
    engineering_references_found: int = 0
    ai_count: int = 0
    ao_count: int = 0
    di_count: int = 0
    do_count: int = 0
    duplicate_records: int = 0
    missing_descriptions: int = 0
    invalid_records: int = 0
    processing_time_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class PCParserService:
    """
    PC Element Parsing Pipeline Service.
    Orchestrates: PDF Reader -> Document Cleaner -> Reference Detector -> Description Mapper -> Validation -> Deduplication -> Excel Generator.
    """

    def __init__(self, job_id: str = None):
        self.job_id = job_id
        self.logger = get_logger(job_id)
        self.pdf_reader = PCPDFReader(job_id)
        self.cleaner = PCDocumentCleaner(job_id)
        self.detector = PCReferenceDetector(job_id)
        self.desc_mapper = PCDescriptionMapper(job_id)
        self.validator = PCElementValidator(job_id)
        self.dedup_checker = PCDuplicateChecker(job_id)
        self.excel_generator = PCExcelGenerator(job_id)

    def parse_pdf_file(self, pdf_path: Path) -> Tuple[List[PCElement], PCAuditStatistics, List[str]]:
        """Parses a PC Element PDF file and executes the complete extraction pipeline."""
        raw_records = self.pdf_reader.extract_line_records(pdf_path)
        return self.parse_line_records(raw_records)

    def parse_line_records(self, raw_records: List[PCLineRecord]) -> Tuple[List[PCElement], PCAuditStatistics, List[str]]:
        """Executes the complete PC Element extraction pipeline on LineRecord stream."""
        start_time = time.time()
        stats = PCAuditStatistics()

        # Stage 1: Read PDF
        stats.pages_read = max((r.page_number for r in raw_records), default=0)
        if not raw_records:
            stats.warnings.append("No line records extracted from PC document.")
            stats.processing_time_seconds = round(time.time() - start_time, 2)
            return [], stats, stats.warnings

        # Stage 2: Document Cleaning
        cleaned_records, ignored_count = self.cleaner.clean_records(raw_records)
        stats.headers_removed = ignored_count

        if not cleaned_records:
            stats.warnings.append("No engineering lines remaining after PCDocumentCleaner.")
            stats.processing_time_seconds = round(time.time() - start_time, 2)
            return [], stats, stats.warnings

        # Stage 3: Detect IO References
        detected_refs = self.detector.detect_references(cleaned_records)
        stats.engineering_references_found = len(detected_refs)

        if not detected_refs:
            stats.warnings.append("No PC Element IO references detected in document.")
            stats.processing_time_seconds = round(time.time() - start_time, 2)
            return [], stats, stats.warnings

        # Stage 4: Attach Nearest Descriptions
        ref_dicts = self.desc_mapper.attach_descriptions(detected_refs, cleaned_records)

        # Stage 5: Validate Elements
        valid_elements, invalid_cnt, val_warnings = self.validator.validate_records(ref_dicts)
        stats.invalid_records = invalid_cnt
        stats.warnings.extend(val_warnings)

        # Stage 6: Deduplicate & Number
        deduped_elements, dup_count = self.dedup_checker.deduplicate_and_number(valid_elements)
        stats.duplicate_records = dup_count

        # Compute category metrics
        for elem in deduped_elements:
            cat_upper = elem.category.upper()
            if not elem.description:
                stats.missing_descriptions += 1

            if cat_upper.startswith("AI"):
                stats.ai_count += 1
            elif cat_upper.startswith("AO"):
                stats.ao_count += 1
            elif cat_upper.startswith("DI"):
                stats.di_count += 1
            elif cat_upper.startswith("DO"):
                stats.do_count += 1

        stats.processing_time_seconds = round(time.time() - start_time, 2)

        # Audit Log Report
        self.logger.info("==================================================")
        self.logger.info("       PC ELEMENT PARSER SERVICE AUDIT REPORT     ")
        self.logger.info("==================================================")
        self.logger.info(f"Pages Read                   : {stats.pages_read}")
        self.logger.info(f"Headers/Footers Removed       : {stats.headers_removed}")
        self.logger.info(f"Engineering References Found : {stats.engineering_references_found}")
        self.logger.info(f"Analog Inputs (AI/AI800)     : {stats.ai_count}")
        self.logger.info(f"Analog Outputs (AO/AO800)    : {stats.ao_count}")
        self.logger.info(f"Digital Inputs (DI/DI800)    : {stats.di_count}")
        self.logger.info(f"Digital Outputs (DO/DO800)   : {stats.do_count}")
        self.logger.info(f"Duplicate Records Removed    : {stats.duplicate_records}")
        self.logger.info(f"Missing Descriptions         : {stats.missing_descriptions}")
        self.logger.info(f"Processing Time              : {stats.processing_time_seconds} s")
        self.logger.info("==================================================")

        return deduped_elements, stats, stats.warnings
