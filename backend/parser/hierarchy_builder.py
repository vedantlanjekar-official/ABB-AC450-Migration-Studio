from typing import Dict, Any, List
from dataclasses import dataclass, field
from backend.parser.card_parser import CardNode
from backend.parser.object_parser import ObjectNode
from backend.parser.family_detector import FamilyDetector
from backend.core.logging import get_logger

@dataclass
class FamilyAST:
    family_name: str
    hardware_defaults: Dict[str, Any] = field(default_factory=dict)
    software_defaults: Dict[str, Any] = field(default_factory=dict)
    cards: Dict[str, CardNode] = field(default_factory=dict)         # CardName -> CardNode
    objects: List[ObjectNode] = field(default_factory=list)          # All ObjectNodes in family

@dataclass
class DocumentAST:
    families: Dict[str, FamilyAST] = field(default_factory=dict)    # FamilyName -> FamilyAST

class HierarchyBuilder:
    """
    Stage 7 — In-Memory AST Hierarchy Builder Module.
    Constructs complete hierarchical engineering AST:
      DocumentAST -> FamilyAST -> (HardwareDefaults, SoftwareDefaults, Cards, Objects)
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)
        self.family_detector = FamilyDetector(job_id)

    def build_document_ast(
        self,
        raw_defaults: Dict[str, Dict[str, Any]],
        raw_cards: List[CardNode],
        raw_objects: List[ObjectNode]
    ) -> DocumentAST:
        """Assembles structured DocumentAST tree from raw default, card, and object nodes."""
        doc_ast = DocumentAST()

        # 1. Initialize Families from raw defaults
        for block_name, params in raw_defaults.items():
            upper = block_name.upper()
            family_key = self.family_detector.normalize_family_name(upper)
            is_software = (len(upper) > 2 and upper.endswith("S") and upper not in ("DS", "TEXT"))

            if family_key not in doc_ast.families:
                doc_ast.families[family_key] = FamilyAST(family_name=family_key)

            fam_ast = doc_ast.families[family_key]
            if is_software:
                fam_ast.software_defaults.update(params)
            else:
                fam_ast.hardware_defaults.update(params)

        # 2. Add Cards to Families
        for card_node in raw_cards:
            family_key = self.family_detector.normalize_family_name(card_node.family)
            if family_key not in doc_ast.families:
                doc_ast.families[family_key] = FamilyAST(family_name=family_key)

            fam_ast = doc_ast.families[family_key]
            fam_ast.cards[card_node.card_name] = card_node

        # 3. Add Objects to Families
        for obj_node in raw_objects:
            family_key = self.family_detector.normalize_family_name(obj_node.family)
            if family_key not in doc_ast.families:
                doc_ast.families[family_key] = FamilyAST(family_name=family_key)

            fam_ast = doc_ast.families[family_key]
            fam_ast.objects.append(obj_node)

        self.logger.info(
            f"HierarchyBuilder built DocumentAST with {len(doc_ast.families)} family node(s) "
            f"containing {sum(len(f.cards) for f in doc_ast.families.values())} card(s) and "
            f"{sum(len(f.objects) for f in doc_ast.families.values())} object(s)."
        )

        return doc_ast
