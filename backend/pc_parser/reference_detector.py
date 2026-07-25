from typing import List, Tuple, Dict, Any
from backend.pc_parser.pdf_reader import PCLineRecord
from backend.pc_parser.grammar_parser import PCGrammarParser
from backend.core.logging import get_logger

class PCReferenceDetector:
    """
    PC Element IO Reference Detector Module.
    Scans line records to locate raw IO references and extract structured grammar objects.
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)
        self.grammar_parser = PCGrammarParser(job_id)

    def detect_references(self, records: List[PCLineRecord]) -> List[Tuple[Dict[str, str], PCLineRecord]]:
        """
        Scans LineRecord stream and extracts all valid IO references.
        Returns List of (parsed_grammar_dict, PCLineRecord).
        """
        detected: List[Tuple[Dict[str, str], PCLineRecord]] = []

        for rec in records:
            parsed = self.grammar_parser.parse_reference(rec.text)
            if parsed:
                detected.append((parsed, rec))

        self.logger.info(f"PCReferenceDetector found {len(detected)} raw IO reference(s) across {len(records)} line(s).")
        return detected
