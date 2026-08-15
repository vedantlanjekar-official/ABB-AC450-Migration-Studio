import time
from pathlib import Path
from typing import List
from datetime import datetime
import threading
import gc
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.parser.pdf_reader import PDFReader, LineRecord
from backend.parser.bax_reader import BaxReader
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
        self.bax_reader = BaxReader(job_id)
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
            # Don't overwrite the final completed/failed user-facing message.
            job = job_store.get_job(self.job_id)
            if job and job.get("status") in {"completed", "failed"}:
                return
            job_store.heartbeat(self.job_id, message=f"{stage}: {detail}" if detail else stage)
        except Exception:
            pass

    def _run_with_heartbeat(self, label: str, fn, *args, **kwargs):
        """Run a long blocking call while emitting heartbeats so stale detection stays quiet."""
        stop = threading.Event()

        def _beat():
            while not stop.wait(15):
                try:
                    stamp = datetime.utcnow().strftime("%H:%M:%S")
                    job_store.heartbeat(
                        self.job_id,
                        message=f"Still working: {label}... ({stamp})",
                    )
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
        """Run the selected PDF or standalone Excel processing workflow."""
        self._pipeline_started_at = datetime.utcnow()
        self._log_stage("START", f"conversion_type={conversion_type.upper()}")
        self.logger.info(
            f"Pipeline environment: upload_dir={settings.UPLOAD_DIR}, "
            f"output_dir={settings.OUTPUT_DIR}, log_dir={settings.LOG_DIR}"
        )
        mode = conversion_type.upper()
        if mode == "PC":
            self._run_pc_conversion_pipeline()
        elif mode in {"COMPARE", "EXCEL", "EXCEL_COMPARE"}:
            self._run_excel_compare_pipeline()
        elif mode in {"IO_ARRANGE", "IO_ADDRESS", "ARRANGE"}:
            self._run_io_address_arrangement_pipeline()
        elif mode in {"ENG_TEMPLATE", "ENGINEERING_TEMPLATE", "ABB_TEMPLATE", "TEMPLATE"}:
            self._run_engineering_template_pipeline()
        else:
            self._run_db_conversion_pipeline()

    def _run_engineering_template_pipeline(self) -> None:
        """Map one generated DB/PC workbook into an ABB engineering import template."""
        from backend.engineering_template import EngineeringTemplateGenerator

        try:
            job = job_store.get_job(self.job_id)
            if not job:
                self.logger.error(f"Job ID {self.job_id} not found in store")
                return

            uploaded_filenames = job.get("uploaded_files", [])
            excel_files = [
                filename
                for filename in uploaded_filenames
                if str(filename).lower().endswith((".xlsx", ".xlsm", ".xls"))
            ]
            if len(excel_files) != 1:
                raise ValueError(
                    "ABB Engineering Template requires exactly one generated "
                    "DB or PB/PC Excel file."
                )

            source_path = settings.UPLOAD_DIR / self.job_id / excel_files[0]
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Uploaded Excel file not found on disk for job {self.job_id}."
                )

            job_store.update_status(
                self.job_id,
                status="reading_pdf",
                progress_percentage=25,
                current_phase="Reading generated engineering workbook",
                conversion_type="ENG_TEMPLATE",
                message=f"Reading clubbed I/O records from {source_path.name}...",
            )
            self._log_stage("ENG TEMPLATE READ", f"source={source_path.name}")

            output_dir = settings.OUTPUT_DIR / self.job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "ABB_Engineering_Template.xlsx"

            job_store.update_status(
                self.job_id,
                status="grouping_elements",
                progress_percentage=55,
                current_phase="Mapping clubbed records into ABB template",
                message="Reusing adjacent AI/AO and DI/DO clubs without re-pairing...",
            )
            result = self._run_with_heartbeat(
                "ABB engineering template",
                EngineeringTemplateGenerator().generate,
                source_path,
                output_path,
            )

            for warning in result.warnings:
                job_store.add_warning(self.job_id, warning)
            if result.skipped_records:
                job_store.add_warning(
                    self.job_id,
                    f"Skipped {result.skipped_records} row(s) without a supported category.",
                )

            elapsed = (datetime.utcnow() - self._pipeline_started_at).total_seconds()
            detected_types = [
                {
                    "element_type": "Paired Clubs",
                    "count": result.paired_clubs,
                    "sample_tags": [
                        str(row.get("$(DEVICETAG1)", ""))
                        for row in result.template_rows[:5]
                        if row.get("$(DEVICETAG2)")
                    ],
                },
                {
                    "element_type": "Singleton Rows",
                    "count": result.singleton_rows,
                    "sample_tags": [
                        str(row.get("$(DEVICETAG1)", ""))
                        for row in result.template_rows[:5]
                        if not row.get("$(DEVICETAG2)")
                    ],
                },
            ]
            self._log_stage(
                "ENG TEMPLATE DONE",
                f"source={result.source_records}, template_rows={len(result.template_rows)}, "
                f"paired={result.paired_clubs}, singletons={result.singleton_rows}",
            )
            job_store.update_status(
                self.job_id,
                status="completed",
                progress_percentage=100,
                current_phase="ABB engineering template complete",
                conversion_type="ENG_TEMPLATE",
                message=(
                    f"Mapped {result.source_records} source record(s) into "
                    f"{len(result.template_rows)} ABB template row(s)."
                ),
                total_objects=len(result.template_rows),
                matched_records=result.paired_clubs,
                unmatched_records=result.singleton_rows,
                detected_element_types=detected_types,
                generated_sheets=result.generated_sheets,
                preview_data=result.preview_data,
                excel_file_path=str(output_path),
                processing_time_seconds=round(elapsed, 2),
            )
        except Exception as exc:
            self.logger.error(
                f"ABB engineering template pipeline failed: {exc}", exc_info=True
            )
            job_store.add_error(self.job_id, str(exc))
            job_store.update_status(
                self.job_id,
                status="failed",
                progress_percentage=100,
                current_phase="ABB engineering template failed",
                conversion_type="ENG_TEMPLATE",
                message=f"ABB engineering template failed: {exc}",
            )

    def _run_io_address_arrangement_pipeline(self) -> None:
        """Rearrange one generated DB/PC workbook into paired ABB addresses."""
        from backend.io_address_arrangement import IOAddressArranger

        try:
            job = job_store.get_job(self.job_id)
            if not job:
                self.logger.error(f"Job ID {self.job_id} not found in store")
                return

            uploaded_filenames = job.get("uploaded_files", [])
            excel_files = [
                filename
                for filename in uploaded_filenames
                if str(filename).lower().endswith((".xlsx", ".xlsm", ".xls"))
            ]
            if len(excel_files) != 1:
                raise ValueError(
                    "I/O Address Arrangement requires exactly one generated DB or PB/PC Excel file."
                )

            source_path = settings.UPLOAD_DIR / self.job_id / excel_files[0]
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Uploaded Excel file not found on disk for job {self.job_id}."
                )

            job_store.update_status(
                self.job_id,
                status="reading_pdf",
                progress_percentage=25,
                current_phase="Reading generated engineering workbook",
                conversion_type="IO_ARRANGE",
                message=f"Reading I/O records from {source_path.name}...",
            )
            self._log_stage("IO ARRANGE READ", f"source={source_path.name}")

            output_dir = settings.OUTPUT_DIR / self.job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "IO_Address_Arrangement.xlsx"

            job_store.update_status(
                self.job_id,
                status="grouping_elements",
                progress_percentage=55,
                current_phase="Grouping records and generating ABB addresses",
                message="Preserving category order and assigning paired 16-channel cards...",
            )
            result = self._run_with_heartbeat(
                "I/O address arrangement",
                IOAddressArranger().arrange,
                source_path,
                output_path,
            )

            if result.skipped_records:
                job_store.add_warning(
                    self.job_id,
                    f"Skipped {result.skipped_records} row(s) without a supported category.",
                )

            elapsed = (datetime.utcnow() - self._pipeline_started_at).total_seconds()
            detected_types = [
                {
                    "element_type": category,
                    "count": count,
                    "sample_tags": [
                        str(record.device_tag)
                        for record in result.records_by_category[category][:5]
                    ],
                }
                for category, count in result.category_counts.items()
            ]
            self._log_stage(
                "IO ARRANGE DONE",
                f"records={result.source_records}, sheets={result.generated_sheets}",
            )
            job_store.update_status(
                self.job_id,
                status="completed",
                progress_percentage=100,
                current_phase="I/O address arrangement complete",
                conversion_type="IO_ARRANGE",
                message=(
                    f"Arranged {result.source_records} I/O record(s) across "
                    f"{len(result.generated_sheets)} category sheet(s)."
                ),
                total_objects=result.source_records,
                detected_element_types=detected_types,
                generated_sheets=result.generated_sheets,
                preview_data=result.preview_data,
                excel_file_path=str(output_path),
                processing_time_seconds=round(elapsed, 2),
            )
        except Exception as exc:
            self.logger.error(
                f"I/O address arrangement pipeline failed: {exc}", exc_info=True
            )
            job_store.add_error(self.job_id, str(exc))
            job_store.update_status(
                self.job_id,
                status="failed",
                progress_percentage=100,
                current_phase="I/O address arrangement failed",
                conversion_type="IO_ARRANGE",
                message=f"I/O address arrangement failed: {exc}",
            )

    def _run_excel_compare_pipeline(self) -> None:
        """Compare ``$(DEVICETAG)`` values symmetrically across two workbooks."""
        from backend.excel_compare.comparator import ExcelComparator
        from backend.excel_compare.report_generator import ComparisonReportGenerator

        try:
            job = job_store.get_job(self.job_id)
            if not job:
                self.logger.error(f"Job ID {self.job_id} not found in store")
                return

            uploaded_filenames = job.get("uploaded_files", [])
            job_upload_dir = settings.UPLOAD_DIR / self.job_id
            self._log_stage(
                "COMPARE INIT",
                f"files={uploaded_filenames}, upload_dir={job_upload_dir}",
            )

            excel_files = [
                f for f in uploaded_filenames
                if str(f).lower().endswith((".xlsx", ".xlsm", ".xls"))
            ]
            if len(excel_files) != 2:
                raise ValueError(
                    "Excel Comparison requires exactly two Excel files: "
                    "each must contain a $(DEVICETAG) column."
                )

            file1 = job_upload_dir / excel_files[0]
            file2 = job_upload_dir / excel_files[1]
            if not file1.exists() or not file2.exists():
                raise FileNotFoundError(
                    f"Uploaded Excel files not found on disk for job {self.job_id}."
                )
            for fpath in (file1, file2):
                if fpath.suffix.lower() == ".xls":
                    raise ValueError(
                        f'Legacy .xls format is not supported ({fpath.name}). '
                        "Please save as .xlsx and retry."
                    )

            job_store.update_status(
                self.job_id,
                status="reading_pdf",
                progress_percentage=20,
                current_phase="Reading Excel worksheets",
                conversion_type="COMPARE",
                message=(
                    f"Locating $(DEVICETAG) in {file1.name} and {file2.name}..."
                ),
            )

            self._log_stage("COMPARE EXTRACT", f"ws1={file1.name}, ws2={file2.name}")
            result = self._run_with_heartbeat(
                "Excel comparison",
                ExcelComparator().compare,
                file1,
                file2,
            )
            self._log_stage(
                "COMPARE EXTRACT",
                f"sheet1={result.worksheet1_sheet} raw={result.worksheet1_raw_rows} "
                f"unique={result.worksheet1_records} dupes={result.worksheet1_duplicates}; "
                f"sheet2={result.worksheet2_sheet} raw={result.worksheet2_raw_rows} "
                f"unique={result.worksheet2_records} dupes={result.worksheet2_duplicates}",
            )
            if result.worksheet1_duplicates or result.worksheet2_duplicates:
                job_store.add_warning(
                    self.job_id,
                    f"Duplicate tags ignored — WS1: {result.worksheet1_duplicates}, "
                    f"WS2: {result.worksheet2_duplicates}.",
                )
            self._log_stage(
                "COMPARE MATCH",
                f"matched={result.matched_records}, unmatched_total={result.unmatched_records}, "
                f"only_file1={len(result.unmatched_in_worksheet1)}, "
                f"only_file2={len(result.unmatched_in_worksheet2)}",
            )

            job_store.update_status(
                self.job_id,
                status="generating_excel",
                progress_percentage=70,
                current_phase="Generating comparison report",
                message="Building Comparison_Report.xlsx...",
                worksheet1_records=result.worksheet1_records,
                worksheet2_records=result.worksheet2_records,
                matched_records=result.matched_records,
                unmatched_records=result.unmatched_records,
                total_objects=result.worksheet1_records,
            )

            output_dir = settings.OUTPUT_DIR / self.job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            report_path = output_dir / "Comparison_Report.xlsx"
            ComparisonReportGenerator().generate(result, report_path)
            preview = ComparisonReportGenerator.build_preview(result)

            elapsed = (datetime.utcnow() - self._pipeline_started_at).total_seconds()
            self._log_stage(
                "COMPARE DONE",
                f"matched={result.matched_records}, unmatched={result.unmatched_records}",
            )

            job_store.update_status(
                self.job_id,
                status="completed",
                progress_percentage=100,
                current_phase="Comparison complete",
                conversion_type="COMPARE",
                message=(
                    f"Comparison complete — {result.matched_records} matched, "
                    f"{result.unmatched_records} unmatched."
                ),
                worksheet1_records=result.worksheet1_records,
                worksheet2_records=result.worksheet2_records,
                matched_records=result.matched_records,
                unmatched_records=result.unmatched_records,
                total_objects=result.worksheet1_records,
                generated_sheets=["Summary", "Unmatched Records"],
                preview_data=preview,
                excel_file_path=str(report_path),
                processing_time_seconds=round(elapsed, 2),
            )
        except Exception as e:
            self.logger.error(f"Excel comparison pipeline failed: {e}", exc_info=True)
            job_store.add_error(self.job_id, str(e))
            job_store.update_status(
                self.job_id,
                status="failed",
                progress_percentage=100,
                current_phase="Comparison failed",
                conversion_type="COMPARE",
                message=f"Excel comparison failed: {e}",
            )

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

            # Phase 1: Reading PC source (PDF or AAX)
            job_store.update_status(
                self.job_id,
                status="reading_pdf",
                progress_percentage=15,
                current_phase="Reading PC Element source (Phase 1)",
                conversion_type="PC",
                message=f"Reading {len(uploaded_filenames)} uploaded PC Element document(s) (PDF/AAX)..."
            )
            time.sleep(0.05)

            from backend.pc_element.parser.parser_service import PCParserService as ModularPCParserService
            from backend.pc_element.parser.excel_generator import ExcelGenerator as PCExcelGenerator
            from backend.pc_element.parser.function_block_extractor import SUPPORTED_FUNCTION_BLOCKS
            from backend.utils.file_utils import combined_export_filename, unique_output_path

            all_objects = []
            combined_fb = {name: 0 for name in SUPPORTED_FUNCTION_BLOCKS}
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
            parsed_sources = 0

            for fname in uploaded_filenames:
                source_path = job_upload_dir / fname
                if not source_path.exists():
                    job_store.add_warning(self.job_id, f"File not found: {fname}")
                    continue

                suffix = source_path.suffix.lower()
                if suffix not in {".pdf", ".aax"}:
                    job_store.add_warning(
                        self.job_id,
                        f"Unsupported PC source type for {fname} (expected .pdf or .aax).",
                    )
                    continue

                # Phase 2: Processing PC Diagram / AAX export
                job_store.update_status(
                    self.job_id,
                    status="extracting_text",
                    progress_percentage=50,
                    current_phase="Extracting Hardwired I/O References & Tag Grammar",
                    conversion_type="PC",
                    message=f"Scanning PC source '{fname}' for hardwired I/O references..."
                )
                time.sleep(0.05)

                self._log_stage("PC STAGE", f"Executing PC parser pipeline for {fname} ({suffix})")
                pc_output_dir = settings.OUTPUT_DIR / self.job_id
                pc_output_dir.mkdir(parents=True, exist_ok=True)
                service = ModularPCParserService(
                    file_path=str(source_path),
                    job_id=self.job_id,
                    output_dir=str(pc_output_dir),
                )
                res = self._run_with_heartbeat(
                    f"PC parse {fname}",
                    service.execute_pipeline,
                    write_excel=False,
                )
                self._log_stage(
                    "PC STAGE",
                    f"PC parser finished for {fname}: io={res.total_io_found}, errors={len(res.errors)}",
                )
                gc.collect()

                parsed_sources += 1
                total_objects += res.total_io_found
                # Roll extended families into summary counters for the UI
                ai_count += res.ai_count + res.ai800_count + res.aic_count
                ao_count += res.ao_count + res.ao800_count + res.aoc_count
                di_count += res.di_count + res.di800_count
                do_count += res.do_count + res.do800_count + res.other_count
                duplicates_removed += res.duplicates_removed
                missing_descriptions += res.descriptions_missing
                total_proc_time += res.processing_time_seconds
                all_objects.extend(res.exported_objects)
                for name, count in (res.function_block_counts or {}).items():
                    combined_fb[name] = combined_fb.get(name, 0) + int(count)

                for w in res.warnings:
                    job_store.add_warning(self.job_id, w)
                for err in res.errors:
                    job_store.add_error(self.job_id, err)
                if res.errors:
                    raise Exception(f"PC Element extraction failed: {res.errors[0]}")

            pc_output_dir = settings.OUTPUT_DIR / self.job_id
            pc_output_dir.mkdir(parents=True, exist_ok=True)
            export_name = combined_export_filename(
                uploaded_filenames,
                suffixes=(".pdf", ".aax"),
                combined_name="PC_Element_IO_List.xlsx",
                fallback="PC_Element.xlsx",
            )
            combined_excel = unique_output_path(pc_output_dir, export_name)
            PCExcelGenerator.generate_excel(
                all_objects,
                str(combined_excel),
                function_block_counts=combined_fb,
            )
            excel_path_str = str(combined_excel)
            total_objects = len(all_objects)
            preview_data = {
                "I_O_List": ModularPCParserService.preview_rows_from_objects(all_objects)
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
                generated_sheets=["I_O_List", "Function Block Summary"],
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
                current_phase="Reading source files (Stage 1)",
                conversion_type="DB",
                message=f"Reading {len(uploaded_filenames)} uploaded DB document(s) (PDF/BAX)...",
            )
            time.sleep(0.05)
            self._log_stage("STAGE 1", "DB source extraction starting (PDF or BAX)")

            from backend.parser.validator import CompilerAuditStatistics
            from backend.models.db_element import DBElement

            all_parsed_elements: List[DBElement] = []
            stats = CompilerAuditStatistics()
            parsed_sources = 0
            duplicate_count = 0

            for fname in uploaded_filenames:
                source_path = job_upload_dir / fname
                if not source_path.exists():
                    msg = f"File not found: {fname} (expected at {source_path})"
                    self._log_stage("STAGE 1 ERROR", msg)
                    job_store.add_warning(self.job_id, msg)
                    continue

                suffix = source_path.suffix.lower()
                self._log_stage(
                    "STAGE 1",
                    f"Extracting lines from {fname} ({source_path.stat().st_size} bytes, type={suffix or 'unknown'})",
                )

                def _page_progress(done: int, total: int, _fname: str = fname) -> None:
                    job_store.heartbeat(
                        self.job_id,
                        message=f"Extracting {_fname}: {done}/{total}...",
                    )

                if suffix == ".bax":
                    file_records = self._run_with_heartbeat(
                        f"BAX extract {fname}",
                        self.bax_reader.extract_line_records,
                        source_path,
                        progress_callback=_page_progress,
                    )
                elif suffix == ".pdf":
                    file_records = self._run_with_heartbeat(
                        f"PDF extract {fname}",
                        self.pdf_reader.extract_line_records,
                        source_path,
                        progress_callback=_page_progress,
                    )
                else:
                    msg = (
                        f"Unsupported DB source type for {fname} "
                        f"(expected .pdf or .bax, got '{suffix or 'none'}')."
                    )
                    self._log_stage("STAGE 1 ERROR", msg)
                    job_store.add_warning(self.job_id, msg)
                    continue

                self._log_stage("STAGE 1", f"Extracted {len(file_records)} line(s) from {fname}")
                gc.collect()
                if not file_records:
                    job_store.add_warning(self.job_id, f"No extractable lines in {fname}.")
                    continue

                job_store.update_status(
                    self.job_id,
                    status="detecting_elements",
                    progress_percentage=45,
                    current_phase="AST Hierarchy & Default Library Building (Stage 4 - 7)",
                    conversion_type="DB",
                    message=f"Parsing DB Element objects in '{fname}'...",
                )
                file_elements, file_stats, file_warnings = self._run_with_heartbeat(
                    f"DB AST parse {fname}",
                    self.parser_service.parse_line_records,
                    file_records,
                    file_name=fname,
                )

                seen_keys = set()
                kept: List[DBElement] = []
                file_dups = 0
                for elem in file_elements:
                    key = ((elem.element_type or "").upper(), (elem.tag or "").upper())
                    if key in seen_keys:
                        file_dups += 1
                        continue
                    seen_keys.add(key)
                    if not elem.file_name:
                        elem.file_name = fname
                    kept.append(elem)

                all_parsed_elements.extend(kept)
                parsed_sources += 1
                duplicate_count += file_dups
                stats.pages_read += file_stats.pages_read
                stats.headers_removed += file_stats.headers_removed
                stats.ignored_header_footer_lines += file_stats.ignored_header_footer_lines
                stats.raw_default_blocks_found += file_stats.raw_default_blocks_found
                stats.hardware_default_blocks += file_stats.hardware_default_blocks
                stats.software_default_blocks += file_stats.software_default_blocks
                stats.merged_profiles_created += file_stats.merged_profiles_created
                stats.objects_parsed += file_stats.objects_parsed
                stats.inherited_parameters += file_stats.inherited_parameters
                stats.object_overrides += file_stats.object_overrides
                stats.missing_parameters_after_merge += file_stats.missing_parameters_after_merge
                stats.warnings.extend(file_stats.warnings)
                stats.processing_time_seconds += file_stats.processing_time_seconds

                self._log_stage(
                    "STAGE 4-7",
                    f"{fname}: parsed={len(file_elements)} kept={len(kept)} "
                    f"dups={file_dups} inherited={file_stats.inherited_parameters}",
                )
                for w in file_warnings:
                    job_store.add_warning(self.job_id, w)
                if file_dups:
                    job_store.add_warning(
                        self.job_id,
                        f"Removed {file_dups} duplicate DB element tag(s) from {fname}.",
                    )

            job_store.update_status(
                self.job_id,
                status="extracting_text",
                progress_percentage=25,
                current_phase="Cleaning Document Noise (Stage 2 & 3)",
                conversion_type="DB",
                message=f"Parsed {parsed_sources} DB document(s) into {len(all_parsed_elements)} object(s)...",
            )
            time.sleep(0.05)

            raw_count = stats.objects_parsed
            if duplicate_count:
                self.logger.info(
                    f"DB within-file dedup removed {duplicate_count} duplicate tag(s); "
                    f"{len(all_parsed_elements)} object(s) remain from {parsed_sources} file(s)."
                )

            total_objects = len(all_parsed_elements)
            self._log_stage(
                "VALIDATION",
                f"files={parsed_sources}, raw_parsed={raw_count}, "
                f"exported={total_objects}, duplicates_removed={duplicate_count}",
            )
            if total_objects == 0:
                job_store.add_warning(self.job_id, "No ABB AC450 DB Element objects detected in provided PDF(s)/BAX file(s).")
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
            # Presentation layer: engineering section order (original Index preserved; pairs adjacent)
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
                preview_data[etype] = rows[:150]

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

            from backend.utils.file_utils import combined_export_filename, unique_output_path

            output_dir = settings.OUTPUT_DIR / self.job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            export_name = combined_export_filename(
                uploaded_filenames,
                suffixes=(".pdf", ".bax"),
                combined_name="DB_Element.xlsx",
                fallback="DB_Element.xlsx",
            )
            output_excel_path = unique_output_path(output_dir, export_name)
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
            ai_count = sum(1 for r in clubbed_rows if r.get("AI") == 1)
            ao_count = sum(1 for r in clubbed_rows if r.get("AO") == 1)
            di_count = sum(1 for r in clubbed_rows if r.get("DI") == 1)
            do_count = sum(1 for r in clubbed_rows if r.get("DO") == 1)
            ai800_count = sum(1 for r in clubbed_rows if r.get("AI800_") == 1)
            ao800_count = sum(1 for r in clubbed_rows if r.get("AO800_") == 1)
            di800_count = sum(1 for r in clubbed_rows if r.get("DI800_") == 1)
            do800_count = sum(1 for r in clubbed_rows if r.get("DO800_") == 1)
            self._log_stage(
                "VALIDATION",
                f"excel_rows={len(clubbed_rows)} "
                f"AI={ai_count} AO={ao_count} DI={di_count} DO={do_count} "
                f"AI800={ai800_count} AO800={ao800_count} DI800={di800_count} DO800={do800_count}",
            )

            elapsed = 0.0
            if self._pipeline_started_at:
                elapsed = (datetime.utcnow() - self._pipeline_started_at).total_seconds()
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
                ai_count=ai_count + ai800_count,
                ao_count=ao_count + ao800_count,
                di_count=di_count + di800_count,
                do_count=do_count + do800_count,
                duplicate_records=duplicate_count,
                detected_element_types=[s.model_dump() for s in detected_summaries],
                generated_sheets=generated_sheets,
                preview_data=preview_data,
                excel_file_path=str(output_excel_path),
                processing_time_seconds=round(elapsed, 2),
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
