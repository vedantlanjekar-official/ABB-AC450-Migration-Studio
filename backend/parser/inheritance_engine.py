from typing import Dict, Any, Tuple, List
from backend.parser.hierarchy_builder import DocumentAST, FamilyAST
from backend.parser.object_parser import ObjectNode
from backend.models.db_element import DBElement
from backend.core.logging import get_logger

class InheritanceEngine:
    """
    Stage 8 — 4-Tier Hierarchical Inheritance Engine Module.
    Executes parameter inheritance in exact priority order:
      1. Hardware Defaults (lowest priority)
      2. Signal Defaults
      3. Card Parameters
      4. Object Parameters (highest priority)
      
    Merge Priority Order:
      Final = {}
      Final.update(HardwareDefaults)
      Final.update(SignalDefaults)
      Final.update(CardParameters)
      Final.update(ObjectParameters)
    """

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def resolve_inheritance(
        self,
        doc_ast: DocumentAST,
        file_name: str = "document.pdf"
    ) -> Tuple[List[DBElement], int, int]:
        """
        Resolves 4-tier inheritance for all ObjectNodes in the DocumentAST tree.
        
        Returns:
            Tuple of (List[DBElement], total_inherited_params_count, total_object_overrides_count)
        """
        resolved_elements: List[DBElement] = []
        total_inherited = 0
        total_overrides = 0

        for family_name, fam_ast in doc_ast.families.items():
            hw_defaults = fam_ast.hardware_defaults
            sw_defaults = fam_ast.software_defaults

            for obj_node in fam_ast.objects:
                final_params: Dict[str, Any] = {}
                inherited_cnt = 0
                overrides_cnt = 0

                # Tier 1: Hardware Defaults
                for k, v in hw_defaults.items():
                    final_params[k] = v
                    inherited_cnt += 1

                # Tier 2: Signal Defaults (overrides Hardware)
                for k, v in sw_defaults.items():
                    if k in final_params:
                        overrides_cnt += 1
                    else:
                        inherited_cnt += 1
                    final_params[k] = v

                # Tier 3: Card Parameters (overrides Hardware & Signal Defaults)
                card_name = obj_node.card_name
                card_node = fam_ast.cards.get(card_name)

                # Fallback card resolution: e.g. index "1.4" -> family "AI" + "1" = "AI1"
                if not card_node and "." in obj_node.index:
                    card_prefix = f"{obj_node.family}{obj_node.index.split('.')[0]}"
                    card_node = fam_ast.cards.get(card_prefix)

                if not card_node and len(fam_ast.cards) == 1:
                    card_node = list(fam_ast.cards.values())[0]

                if card_node:
                    for k, v in card_node.parameters.items():
                        if k in final_params:
                            overrides_cnt += 1
                        else:
                            inherited_cnt += 1
                        final_params[k] = v

                # Tier 4: Object Parameters (highest priority, overrides everything)
                for k, v in obj_node.parameters.items():
                    if k in final_params:
                        overrides_cnt += 1
                    final_params[k] = v

                db_elem = DBElement(
                    tag=obj_node.identifier,
                    element_type=obj_node.family,
                    element_index=obj_node.index,
                    parameters=final_params,
                    raw_text="\n".join(obj_node.raw_lines),
                    page_number=obj_node.page_number,
                    file_name=file_name
                )

                resolved_elements.append(db_elem)
                total_inherited += inherited_cnt
                total_overrides += overrides_cnt

        self.logger.info(
            f"InheritanceEngine resolved {len(resolved_elements)} object(s) "
            f"({total_inherited} inherited params, {total_overrides} overrides)."
        )

        return resolved_elements, total_inherited, total_overrides
