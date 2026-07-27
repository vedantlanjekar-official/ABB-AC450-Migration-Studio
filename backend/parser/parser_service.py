import time
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.models.db_element import DBElement
from backend.constants.ac450_constants import SUPPORTED_DB_ELEMENT_TYPES
from backend.parser.pdf_reader import PDFReader, LineRecord
from backend.parser.document_cleaner import DocumentCleaner
from backend.parser.family_detector import FamilyDetector
from backend.parser.default_parser import DefaultParser
from backend.parser.card_parser import CardParser, CardNode
from backend.parser.object_parser import ObjectParser, ObjectNode
from backend.parser.hierarchy_builder import HierarchyBuilder, DocumentAST
from backend.parser.inheritance_engine import InheritanceEngine
from backend.parser.validator import ElementValidator, CompilerAuditStatistics
from backend.core.logging import get_logger

class ParserService:
    """
    Grammar-Based Hierarchical AST Compiler Parser Service.
    
    9 Stages:
      Stage 1: PDF Line Reader (pdf_reader.py)
      Stage 2: Document Metadata Cleaning (document_cleaner.py)
      Stage 3: Dynamic Family Boundary Detection (family_detector.py)
      Stage 4: Hardware & Signal Default Parsing (default_parser.py)
      Stage 5: Card Definition Node Parsing (card_parser.py)
      Stage 6: Signal Element Object Node Parsing (object_parser.py)
      Stage 7: In-Memory AST Hierarchy Building (hierarchy_builder.py)
      Stage 8: 4-Tier Inheritance Engine (inheritance_engine.py)
      Stage 9: Validation & Excel Generation (validator.py & excel_generator.py)
    """

    def __init__(self, job_id: str = None):
        self.job_id = job_id
        self.logger = get_logger(job_id)
        self.pdf_reader = PDFReader(job_id)
        self.document_cleaner = DocumentCleaner(job_id)
        self.family_detector = FamilyDetector(job_id)
        self.default_parser = DefaultParser(job_id)
        self.card_parser = CardParser(job_id)
        self.object_parser = ObjectParser(job_id)
        self.hierarchy_builder = HierarchyBuilder(job_id)
        self.inheritance_engine = InheritanceEngine(job_id)
        self.validator = ElementValidator(job_id)

    def parse_pdf_file(
        self,
        pdf_path: Path
    ) -> Tuple[List[DBElement], CompilerAuditStatistics, List[str]]:
        """Parses a PDF file using the Hierarchical AST Compiler Pipeline."""
        records = self.pdf_reader.extract_line_records(pdf_path)
        return self.parse_line_records(records, file_name=pdf_path.name)

    def parse_document_pages(
        self,
        pages: List[Dict[str, Any]],
        file_name: str = "document.pdf"
    ) -> Tuple[List[DBElement], CompilerAuditStatistics, List[str]]:
        """Adapter converting legacy pages dict list into LineRecords."""
        records: List[LineRecord] = []
        for p_idx, p in enumerate(pages, start=1):
            page_num = p.get("page_number", p_idx)
            text = p.get("text", "")
            for l_idx, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    records.append(LineRecord(page_number=page_num, line_number=l_idx, text=line.strip()))
        return self.parse_line_records(records, file_name=file_name)

    def parse_line_records(
        self,
        raw_records: List[LineRecord],
        file_name: str = "document.pdf"
    ) -> Tuple[List[DBElement], CompilerAuditStatistics, List[str]]:
        """Executes the complete 9-Stage AST Compiler Pipeline."""
        start_time = time.time()
        stats = CompilerAuditStatistics()

        # Stage 1: PDF Reader
        stats.pages_read = max((r.page_number for r in raw_records), default=0)
        if not raw_records:
            stats.warnings.append(f"No line records extracted from {file_name}")
            stats.processing_time_seconds = round(time.time() - start_time, 2)
            return [], stats, stats.warnings

        # Stage 2: Document Noise Cleaning
        cleaned_records, ignored_count = self.document_cleaner.clean_line_records(raw_records)
        stats.headers_removed = ignored_count
        stats.ignored_header_footer_lines = ignored_count

        if not cleaned_records:
            stats.warnings.append(f"No engineering text remaining after cleaning in {file_name}")
            stats.processing_time_seconds = round(time.time() - start_time, 2)
            return [], stats, stats.warnings

        # Stage 3, 4, 5, 6: Node Partitioning & Extraction
        raw_defaults: Dict[str, Dict[str, Any]] = {}
        raw_cards: List[CardNode] = []
        raw_objects: List[ObjectNode] = []

        current_block_type: str = None   # "DEFAULT", "CARD", "OBJECT"
        current_block_name: str = None
        current_card_name: str = "DEFAULT_CARD"
        current_family: str = None
        current_object_info: Tuple[str, str, str] = None
        current_buffer: List[LineRecord] = []

        def flush_active_block():
            nonlocal current_block_type, current_block_name, current_card_name, current_family, current_object_info, current_buffer
            if not current_buffer:
                return

            if current_block_type == "DEFAULT" and current_block_name:
                parsed_params = self.default_parser.parse_default_lines(current_block_name, current_buffer)
                if current_block_name in raw_defaults:
                    raw_defaults[current_block_name].update(parsed_params)
                else:
                    raw_defaults[current_block_name] = parsed_params

            elif current_block_type in ("CARD", "OBJECT") and (current_object_info or current_block_name):
                has_name = any(re.search(r'^\s*:NAME\b', rec.text, re.IGNORECASE) for rec in current_buffer)
                
                family, index, identifier = current_object_info if current_object_info else (current_family, "1", current_block_name)

                # Card Node: Lacks :NAME parameter AND index has no dot (e.g. AI1, AI2, AO1, DI1)
                if not has_name and "." not in index:
                    card_node = self.card_parser.parse_card_records(
                        card_name=identifier,
                        family=family or "AI",
                        records=current_buffer
                    )
                    raw_cards.append(card_node)
                    current_card_name = identifier
                else:
                    # Actual Signal Object Node: Has :NAME or dot index (e.g. AI1.1, PIDCON1, MOTCON1)
                    obj_node = self.object_parser.parse_object_records(
                        family=family,
                        card_name=current_card_name,
                        identifier=identifier,
                        index=index,
                        records=current_buffer
                    )
                    raw_objects.append(obj_node)

            current_buffer = []

        # Stream Line Partitioning Loop
        for rec in cleaned_records:
            line_str = rec.text.strip()

            # 1. Check *** END OF DEFAULTS ***
            if "END OF DEFAULT" in line_str.upper():
                flush_active_block()
                current_block_type = None
                continue

            # 2. Check DEFAULT header (Node Type 1 / 2)
            # Keep defaults only for supported I/O families (and their *S software variants).
            match_def = self.family_detector.DEFAULT_FAMILY_REGEX.match(line_str)
            if match_def or line_str.upper().startswith("DEFAULT"):
                raw_name = match_def.group(1).upper() if match_def else line_str.split()[1].strip(":-_").upper() if len(line_str.split()) >= 2 else ""
                if raw_name and raw_name not in ("OF", "DEFAULTS", "BLOCK", "SECTION"):
                    flush_active_block()
                    normalized_family = self.family_detector.normalize_family_name(raw_name)
                    if normalized_family not in SUPPORTED_DB_ELEMENT_TYPES:
                        current_block_type = None
                        current_buffer = []
                        continue
                    current_block_type = "DEFAULT"
                    current_block_name = raw_name
                    current_family = normalized_family or current_family
                    current_buffer = [rec]
                    continue

            # 3. Check Card Definition header (Node Type 3 e.g. AI1 AI, AI2 AI, AO1 AO)
            card_hdr = self.card_parser.is_card_header(line_str)
            if card_hdr:
                c_name, c_fam = card_hdr
                flush_active_block()
                if c_fam.upper() not in SUPPORTED_DB_ELEMENT_TYPES:
                    current_block_type = None
                    current_buffer = []
                    continue
                current_block_type = "CARD"
                current_block_name = c_name
                current_card_name = c_name
                current_family = c_fam
                current_object_info = (c_fam, c_name.replace(c_fam, ""), c_name)
                current_buffer = [rec]
                continue

            # 4. Check Signal Object header (Node Type 4 e.g. AI1.1, AI2.14, AO3.8, AI8001.1)
            # Skip every object whose family is outside the eight supported I/O types.
            obj_hdr = self.object_parser.is_object_header(line_str)
            if obj_hdr:
                family, index, identifier = obj_hdr
                flush_active_block()
                if family.upper() not in SUPPORTED_DB_ELEMENT_TYPES:
                    current_block_type = None
                    current_buffer = []
                    continue
                current_block_type = "OBJECT"
                current_object_info = obj_hdr
                current_family = family
                current_buffer = [rec]
                continue

            # Accumulate lines into active block
            if current_block_type:
                current_buffer.append(rec)

        # Flush trailing block at EOF
        flush_active_block()

        # Stage 7: Build In-Memory AST Hierarchy
        doc_ast = self.hierarchy_builder.build_document_ast(
            raw_defaults=raw_defaults,
            raw_cards=raw_cards,
            raw_objects=raw_objects
        )

        stats.raw_default_blocks_found = len(raw_defaults)
        stats.hardware_default_blocks = sum(1 for f in doc_ast.families.values() if f.hardware_defaults)
        stats.software_default_blocks = sum(1 for f in doc_ast.families.values() if f.software_defaults)
        stats.merged_profiles_created = len(doc_ast.families)

        # Stage 8: Resolve 4-Tier Inheritance (Hardware -> Software -> Card -> Object)
        resolved_elements, inherited_cnt, overrides_cnt = self.inheritance_engine.resolve_inheritance(
            doc_ast=doc_ast,
            file_name=file_name
        )

        stats.objects_parsed = len(resolved_elements)
        stats.inherited_parameters = inherited_cnt
        stats.object_overrides = overrides_cnt

        # Stage 9: Validation & Statistics Report
        validated_elements, missing_cnt, val_warnings = self.validator.validate_elements(resolved_elements)
        stats.missing_parameters_after_merge = missing_cnt
        stats.warnings.extend(val_warnings)
        stats.processing_time_seconds = round(time.time() - start_time, 2)

        # Audit Report Log
        self.logger.info("==================================================")
        self.logger.info("  HIERARCHICAL AST COMPILER ENGINE AUDIT REPORT   ")
        self.logger.info("==================================================")
        self.logger.info(f"Stage 1: Pages Read               : {stats.pages_read}")
        self.logger.info(f"Stage 2: Metadata Headers Removed : {stats.headers_removed}")
        self.logger.info(f"Stage 3 & 4: Families Detected    : {len(doc_ast.families)}")
        self.logger.info(f"Stage 5: Cards Parsed (Parent AST): {sum(len(f.cards) for f in doc_ast.families.values())}")
        self.logger.info(f"Stage 6: Signal Objects Parsed    : {stats.objects_parsed}")
        self.logger.info(f"Stage 8: Inherited Parameters     : {stats.inherited_parameters}")
        self.logger.info(f"Stage 8: Object Overrides         : {stats.object_overrides}")
        self.logger.info(f"Warnings                          : {len(stats.warnings)}")
        self.logger.info(f"Processing Time                   : {stats.processing_time_seconds} s")
        self.logger.info("==================================================")

        return validated_elements, stats, stats.warnings
