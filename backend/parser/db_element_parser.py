from typing import List, Dict, Any, Tuple
from backend.models.db_element import DBElement
from backend.parser.parser_service import ParserService
from backend.core.logging import get_logger

class DBElementParser:
    """
    Adapter/Wrapper for ParserService providing backwards compatibility.
    Orchestrates 10-Stage Compiler-Style ABB AC450 DB Parsing.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)
        self.service = ParserService(job_id)

    def parse_pages(self, pages: List[Dict[str, Any]], file_name: str = "document.pdf") -> Tuple[List[DBElement], List[str]]:
        """
        Parses page text streams into a list of merged DBElement objects.
        """
        merged_elements, stats, warnings = self.service.parse_document_pages(pages, file_name=file_name)
        return merged_elements, warnings
