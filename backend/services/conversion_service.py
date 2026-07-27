import time
from pathlib import Path
from typing import List
from datetime import datetime
import threading
import gc
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.parser.pdf_reader import PDFReader, LineRecord
from backend.parser.parser_service import ParserService
from backend.mapper.element_mapper import ElementMapper
from backend.mapper.record_clubber import RecordClubber
from backend.mapper.output_formatter import OutputFormatter
from backend.excel.excel_generator import ExcelGenerator
from backend.pc_parser.pdf_reader import PCPDFReader, PCLineRecord
from backend.pc_parser.parser_service import PCParserService
from backend.pc_parser.excel_generator import PCExcelGenerator
from backend.services.job_manager import job_store
from backend.schemas.api_schemas import ElementTypeSummary

class ConversionService:
    """
    Orchestrates both DB Element Compiler Pipeline and PC Element Converter Pipeline across all uploaded PDF files.
    Executes in a dedicated background worker thread pool to keep the FastAPI event loop 100% unblocked for status polling.
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.logger = get_logger(job_id)
        self._pipeline_started_at: datetime | None = None
        self.pdf_reader = PDFReader(job_id)
        self.parser_service = ParserService(job_id)
        self.mapper = ElementMapper(job_id)
        self.record_clubber = RecordClubber(job_id)
        self.output_formatter = OutputFormatter(job_id)
        self.excel_generator = ExcelGenerator(job_id)
        self.pc_pdf_reader = PCPDFReader(job_id)
        self.pc_parser_service = PCParserService(job_id)
        self.pc_excel_generator = PCExcelGenerator(job_id)

    def _log_stage(self, stage: str, detail: str = "") -> None:
        """Write a structured pipeline stage marker to the job log."""
        elapsed = ""
        if self._pipeline_started_at:
            elapsed = f" (+{(datetime.utcnow() - self._pipeline_started_at).total_seconds():.2f}s)"
        message = f"[PIPELINE STAGE] {stage}{elapsed}"
        if detail:
            message = f"{message} — {detail}"
        self.logger.info(message)
        try:
            job_store.heartbeat(self.job_id, message=f"{stage}: {detail}" if detail else stage)
        except Exception:
            pass

    def _run_with_heartbeat(self, label: str, fn, *args, **kwargs):
        """Run a long blocking call while emitting heartbeats so stale detection stays quiet."""
        stop = threading.Event()

        def _beat():
            while not stop.wait(15):
                try:
                    job_store.heartbeat(self.job_id, message=f"Still working: {label}...")
                except Exception:
                    pass

        thread = threading.Thread(target=_beat, daemon=True, name=f"hb-{self.job_id[:8]}")
        thread.start()
        try:
            return fn(*args, **kwargs)
        finally:
            stop.set()
            thread.join(timeout=1)

    def run_conversion_pipeline(self, conversion_type: str = "DB") -> None:
        """Runs DB or PC conversion pipeline across all uploaded files and updates job status."""
        self._pipeline_started_at = datetime.utcnow()
        self._log_stage("START", f"conversion_type={conversion_type.upper()}")
        self.logger.info(
            f"Pipeline environment: upload_dir={settings.UPLOAD_DIR}, "
            f"output_dir={settings.OUTPUT_DIR}, log_dir={settings.LOG_DIR}"
        )
        if conversion_type.upper() == "PC":
            self._run_pc_conversion_pipeline()
        else:
            self._run_db_conversion_pipeline()

    def _run_pc_conversion_pipeline(self) -> None:
        """Executes PC Element extraction pipeline using backend.pc_element module."""
        try:
            job = job_store.get_job(self.job_id)
            if not job:
                self.logger.error(f"Job ID {self.job_id} not found in store")
                return

            uploaded_filenames = job.get("uploaded_files", [])
            job_upload_dir = settings.UPLOAD_DIR / self.job_id
            self._log_stage(
                "PC INIT",
                f"files={uploaded_filenames}, upload_dir={job_upload_dir}, dir_exists={job_upload_dir.exists()}",
            )

            # Phase 1: Reading PDF
            job_store.update_status(
                self.job_id,
                status="reading_pdf",
                progress_percentage=15,
                current_phase="Reading PC Element PDF (Phase 1)",
                conversion_type="PC",
                message=f"Reading {len(uploaded_filenames)} uploaded PC Element PDF document(s)..."
            )
            time.sleep(0.05)

            from backend.pc_element.parser.parser_service import PCParserService as ModularPCParserService

            all_previews = []
            total_objects = 0
            ai_count = 0
            ai800_count = 0
            ao_count = 0
            ao800_count = 0
            di_count = 0
            di800_count = 0
            do_count = 0
            do800_count = 0
            duplicates_removed = 0
            missing_descriptions = 0
            excel_path_str = None
            total_proc_time = 0.0

            for fname in uploaded_filenames:
                pdf_path = job_upload_dir / fname
                if not pdf_path.exists():
                    job_store.add_warning(self.job_id, f"File not found: {fname}")
                    continue

                # Phase 2: Processing PC Diagram PDF
                job_store.update_status(
                    self.job_id,
                    status="extracting_text",
                    progress_percentage=50,
                    current_phase="Extracting Hardwired I/O References & Tag Grammar",
                    conversion_type="PC",
                    message=f"Scanning PC Diagram '{fname}' for hardwired I/O references..."
                )
                time.sleep(0.05)

                self._log_stage("PC STAGE", f"Executing PC parser pipeline for {fname}")
                service = ModularPCParserService(
                    file_path=str(pdf_path),
                    job_id=self.job_id,
                    output_dir=str(settings.OUTPUT_DIR)
                )
                res = self._run_with_heartbeat(
                    f"PC parse {fname}",
                    service.execute_pipeline,
                )
                self._log_stage(
                    "PC STAGE",
                    f"PC parser finished for {fname}: io={res.total_io_found}, errors={len(res.errors)}",
                )
                gc.collect()

                total_objects += res.total_io_found
                # Roll extended families into summary counters for the UI
                ai_count += res.ai_count + res.ai800_count + res.aic_count
                ao_count += res.ao_count + res.ao800_count + res.aoc_count
                di_count += res.di_count + res.di800_count
                do_count += res.do_count + res.do800_count + res.other_count
                duplicates_removed += res.duplicates_removed
                missing_descriptions += res.descriptions_missing
                total_proc_time += res.processing_time_seconds
                if res.excel_file_path:
                    excel_path_str = res.excel_file_path
                all_previews.extend(res.preview_data)

                for w in res.warnings:
                    job_store.add_warning(self.job_id, w)
                for err in res.errors:
                    job_store.add_error(self.job_id, err)
                if res.errors:
                    raise Exception(f"PC Element extraction failed: {res.errors[0]}")

            preview_data = {
                "I_O_List": all_previews[:50]
            }

            # Phase 4: Completed
            job_store.update_status(
                self.job_id,
                status="completed",
                progress_percentage=100,
                current_phase="Completed",
                conversion_type="PC",
                total_objects=total_objects,
                ai_count=ai_count,
                ao_count=ao_count,
                di_count=di_count,
                do_count=do_count,
                duplicate_records=duplicates_removed,
                missing_descriptions=missing_descriptions,
                processing_time_seconds=round(total_proc_time, 2),
                generated_sheets=["I_O_List"],
                preview_data=preview_data,
                excel_file_path=excel_path_str,
                message=f"PC Element Conversion complete! Extracted {total_objects} hardwired I/O reference(s) into Valmet Excel I_O_List."
            )
            self.logger.info(f"PC Conversion Pipeline finished successfully for job {self.job_id}")

        except Exception as e:
            self.logger.error(f"PC Conversion Pipeline error for job {self.job_id}: {e}", exc_info=True)
            job_store.add_error(self.job_id, str(e))
            job_store.update_status(
                self.job_id,
                status="failed",
                progress_percentage=100,
                current_phase="Failed",
                conversion_type="PC",
                message=f"PC Processing failed: {str(e)}"
            )

    def _run_db_conversion_pipeline(self) -> None:
        """Executes DB Element extraction pipeline."""
        try:
            job = job_store.get_job(self.job_id)
            if not job:
                self.logger.error(f"Job ID {self.job_id} not found in store")
                return

            uploaded_filenames = job.get("uploaded_files", [])
            job_upload_dir = settings.UPLOAD_DIR / self.job_id
            self._log_stage(
                "INIT",
                f"files={uploaded_filenames}, upload_dir={job_upload_dir}, dir_exists={job_upload_dir.exists()}",
            )

            job_store.update_status(
                self.job_id,
                status="reading_pdf",
                progress_percentage=10,
                current_phase="Reading PDF files (Stage 1)",
                conversion_type="DB",
                message=f"Reading {len(uploaded_filenames)} uploaded PDF document(s)..."
            )
            time.sleep(0.05)
            self._log_stage("STAGE 1", "PDF document extraction starting")

            combined_line_records: List[LineRecord] = []
            page_offset = 0

            for fname in uploaded_filenames:
                pdf_path = job_upload_dir / fname
                if not pdf_path.exists():
                    msg = f"File not found: {fname} (expected at {pdf_path})"
                    self._log_stage("STAGE 1 ERROR", msg)
                    job_store.add_warning(self.job_id, msg)
                    continue

                self._log_stage("STAGE 1", f"Extracting lines from {fname} ({pdf_path.stat().st_size} bytes)")
                file_records = self._run_with_heartbeat(
                    f"PDF extract {fname}",
                    self.pdf_reader.extract_line_records,
                    pdf_path,
                )
                self._log_stage("STAGE 1", f"Extracted {len(file_records)} line(s) from {fname}")
                gc.collect()
                if file_records:
                    max_page_in_file = max(r.page_number for r in file_records)
                    for rec in file_records:
                        combined_line_records.append(
                            LineRecord(
                                page_number=rec.page_number + page_offset,
                                line_number=rec.line_number,
                                text=rec.text
                            )
                        )
                    page_offset += max_page_in_file

            job_store.update_status(
                self.job_id,
                status="extracting_text",
                progress_percentage=25,
                current_phase="Cleaning Document Noise (Stage 2 & 3)",
                conversion_type="DB",
                message=f"Cleaning repeated page headers and footers across {len(combined_line_records)} line records..."
            )
            time.sleep(0.05)
            self._log_stage("STAGE 2-3", f"Document cleaning complete — {len(combined_line_records)} combined line record(s)")

            job_store.update_status(
                self.job_id,
                status="detecting_elements",
                progress_percentage=45,
                current_phase="AST Hierarchy & Default Library Building (Stage 4 - 7)",
                conversion_type="DB",
                message="Building unified Default Library and Card/Object AST Tree..."
            )
            time.sleep(0.05)
            self._log_stage("STAGE 4-7", "AST hierarchy and default library building starting")

            combined_file_name = ", ".join(uploaded_filenames) if uploaded_filenames else "document.pdf"
            all_parsed_elements, stats, warnings = self._run_with_heartbeat(
                "DB AST parse",
                self.parser_service.parse_line_records,
                combined_line_records,
                file_name=combined_file_name,
            )
            self._log_stage(
                "STAGE 4-7",
                f"Parsed {len(all_parsed_elements)} object(s), "
                f"{stats.raw_default_blocks_found} default block(s), "
                f"{stats.inherited_parameters} inherited parameter(s)",
            )

            for w in warnings:
                job_store.add_warning(self.job_id, w)

            total_objects = len(all_parsed_elements)
            if total_objects == 0:
                job_store.add_warning(self.job_id, "No ABB AC450 DB Element objects detected in provided PDF(s).")
                self._log_stage("STAGE 4-7 WARNING", "Zero DB elements detected after parsing")

            job_store.update_status(
                self.job_id,
                status="grouping_elements",
                progress_percentage=75,
                current_phase="Applying Merged Defaults & Tabular Grouping (Stage 8 & 9)",
                conversion_type="DB",
                message=f"Applying merged family default profiles to {total_objects} objects..."
            )
            time.sleep(0.05)
            self._log_stage("STAGE 8-9", f"Grouping and mapping {total_objects} object(s)")

            # Club records by Loop Tag (matching only — does not define final sheet order)
            clubbed_elements = self.record_clubber.club_elements(all_parsed_elements)
            self._log_stage("STAGE 8-9", f"Record clubbing applied to {len(clubbed_elements)} object(s)")

            clubbed_rows = self.mapper.map_clubbed(clubbed_elements)
            # Presentation layer: engineering section order + sequential Index (pairs preserved)
            formatted_rows = self.output_formatter.format_clubbed_rows(clubbed_rows)
            mapped_sheets = {"Clubbed_IO": formatted_rows} if formatted_rows else {}
            self._log_stage(
                "STAGE 8-9",
                f"Formatted {len(formatted_rows)} row(s) into engineering sequence "
                f"(AI→AO, DO→DI, AI800→AO800, DO800→DI800)",
            )

            detected_summaries = []
            preview_data = {}
            for etype, rows in mapped_sheets.items():
                sample_tags = [r["Tag"] for r in rows[:5]]
                detected_summaries.append(
                    ElementTypeSummary(
                        element_type=etype,
                        count=len(rows),
                        sample_tags=sample_tags
                    )
                )
                preview_data[etype] = rows[:10]

            job_store.update_status(
                self.job_id,
                status="generating_excel",
                progress_percentage=90,
                current_phase="Generating Valmet Excel Workbook (Stage 9)",
                conversion_type="DB",
                message="Building consolidated openpyxl Excel workbook..."
            )
            time.sleep(0.05)
            self._log_stage("STAGE 10", "Excel workbook generation starting")

            settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_excel_path = settings.OUTPUT_DIR / f"{self.job_id}_valmet_export.xlsx"
            generated_sheets = self.excel_generator.generate_workbook(mapped_sheets, output_excel_path)
            excel_exists = output_excel_path.exists()
            excel_size = output_excel_path.stat().st_size if excel_exists else 0
            self._log_stage(
                "STAGE 10",
                f"Excel written to {output_excel_path} (exists={excel_exists}, size={excel_size} bytes)",
            )
            if not excel_exists:
                raise FileNotFoundError(f"Excel workbook was not created at {output_excel_path}")

            clubbed_rows = mapped_sheets.get("Clubbed_IO", [])
            ai_count = sum(1 for r in clubbed_rows if r.get("Category") == "AI")
            ao_count = sum(1 for r in clubbed_rows if r.get("Category") == "AO")
            di_count = sum(1 for r in clubbed_rows if r.get("Category") == "DI")
            do_count = sum(1 for r in clubbed_rows if r.get("Category") == "DO")

            job_store.update_status(
                self.job_id,
                status="completed",
                progress_percentage=100,
                current_phase="Completed",
                conversion_type="DB",
                total_objects=total_objects,
                default_sections_found=stats.raw_default_blocks_found,
                hardware_default_blocks=stats.hardware_default_blocks,
                software_default_blocks=stats.software_default_blocks,
                merged_profiles_created=stats.merged_profiles_created,
                objects_inherited_defaults=total_objects,
                parameters_filled_from_defaults=stats.inherited_parameters,
                object_overrides=stats.object_overrides,
                missing_parameters_after_merge=stats.missing_parameters_after_merge,
                ignored_header_footer_lines=stats.headers_removed,
                ai_count=ai_count,
                ao_count=ao_count,
                di_count=di_count,
                do_count=do_count,
                detected_element_types=[s.model_dump() for s in detected_summaries],
                generated_sheets=generated_sheets,
                preview_data=preview_data,
                excel_file_path=str(output_excel_path),
                message=f"Conversion complete! Processed {total_objects} objects ({stats.inherited_parameters} inherited params) in consolidated worksheet."
            )
            self._log_stage("COMPLETE", f"DB conversion finished — {total_objects} object(s), 1 worksheet")
            self.logger.info(f"DB Conversion Pipeline finished successfully for job {self.job_id}")

        except Exception as e:
            self._log_stage("FAILED", str(e))
            self.logger.error(f"DB Conversion Pipeline error for job {self.job_id}: {e}", exc_info=True)
            job_store.add_error(self.job_id, str(e))
            job_store.update_status(
                self.job_id,
                status="failed",
                progress_percentage=100,
                current_phase="Failed",
                conversion_type="DB",
                message=f"DB Processing failed: {str(e)}"
            )
