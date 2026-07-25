from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from backend.models.db_element import DBElement
from backend.parser.default_mapper import DefaultMapper
from backend.core.logging import get_logger

@dataclass
class SectionMetric:
    section_name: str
    element_type: str
    objects_count: int = 0
    inherited_params: int = 0
    explicit_params: int = 0

@dataclass
class SequentialParsingStatistics:
    default_sections_found: int = 0
    total_objects_parsed: int = 0
    total_inherited_parameters: int = 0
    total_explicit_parameters: int = 0
    missing_parameters_after_merge: int = 0
    section_metrics: List[SectionMetric] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class ParserStateManager:
    """
    State Manager for Sequential ABB AC450 DB Parser.
    Maintains active section state, current active defaults, section transition lifecycle,
    and section-by-section audit statistics.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)
        self.default_mapper = DefaultMapper(job_id=job_id)
        
        self.active_section_raw: Optional[str] = None
        self.active_section_type: Optional[str] = None
        self.active_defaults: Dict[str, Any] = {}
        
        self.completed_elements: List[DBElement] = []
        self.stats = SequentialParsingStatistics()
        self.current_section_metric: Optional[SectionMetric] = None

    def start_new_section(self, raw_default_name: str):
        """
        Handles transition to a new DEFAULT section.
        Completes previous section and sets up new active section defaults context.
        """
        if self.active_section_raw:
            self.complete_current_section()

        element_type = self.default_mapper.resolve_element_type(raw_default_name)
        self.active_section_raw = raw_default_name
        self.active_section_type = element_type
        self.active_defaults = {}

        self.stats.default_sections_found += 1
        self.current_section_metric = SectionMetric(
            section_name=raw_default_name,
            element_type=element_type
        )

        self.logger.info(f"Detected DEFAULT Section: {raw_default_name} (Target Type: {element_type})")
        self.logger.info(f"Current Section : {element_type}")

    def set_active_defaults(self, default_params: Dict[str, Any]):
        """Sets active defaults for the current section."""
        self.active_defaults = dict(default_params)
        self.logger.info(
            f"Stored {len(default_params)} active default parameter(s) for Section '{self.active_section_type}'"
        )

    def add_merged_element(
        self,
        element: DBElement,
        inherited_count: int,
        explicit_count: int
    ):
        """Adds a merged DBElement object and updates section & global metrics."""
        self.completed_elements.append(element)
        self.stats.total_objects_parsed += 1
        self.stats.total_inherited_parameters += inherited_count
        self.stats.total_explicit_parameters += explicit_count

        if self.current_section_metric:
            self.current_section_metric.objects_count += 1
            self.current_section_metric.inherited_params += inherited_count
            self.current_section_metric.explicit_params += explicit_count

        # Check missing mandatory :NAME parameter
        if not element.get_parameter("NAME"):
            self.stats.missing_parameters_after_merge += 1
            warn = f"Object '{element.tag}' on page {element.page_number} is missing mandatory ':NAME' parameter."
            if warn not in self.stats.warnings:
                self.stats.warnings.append(warn)

    def complete_current_section(self):
        """Logs section completion metrics and saves section statistics."""
        if self.current_section_metric:
            sec = self.current_section_metric
            self.logger.info(f"Section Completed : {sec.element_type}")
            self.logger.info(
                f"  Objects Parsed       : {sec.objects_count}\n"
                f"  Inherited Parameters : {sec.inherited_params}\n"
                f"  Explicit Parameters  : {sec.explicit_params}"
            )
            self.stats.section_metrics.append(sec)
            self.current_section_metric = None

    def finalize_document(self) -> Tuple[List[DBElement], SequentialParsingStatistics]:
        """Flushes final active section and returns completed elements & stats."""
        if self.current_section_metric:
            self.complete_current_section()

        self.logger.info("==================================================")
        self.logger.info("   SEQUENTIAL STATE MACHINE PARSING COMPLETED    ")
        self.logger.info("==================================================")
        self.logger.info(f"Detected DEFAULT Sections : {self.stats.default_sections_found}")
        self.logger.info(f"Total Objects Parsed     : {self.stats.total_objects_parsed}")
        self.logger.info(f"Inherited Parameters     : {self.stats.total_inherited_parameters}")
        self.logger.info(f"Explicit Parameters      : {self.stats.total_explicit_parameters}")
        self.logger.info(f"Warnings                 : {len(self.stats.warnings)}")
        self.logger.info("==================================================")

        return self.completed_elements, self.stats
