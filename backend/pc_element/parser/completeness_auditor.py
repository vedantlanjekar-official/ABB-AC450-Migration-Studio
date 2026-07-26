"""
completeness_auditor.py - Engineering completeness checks + validation report writer.

Validates category balance (e.g. DO present without DI), reports extraction accuracy
against a document-wide inventory, and writes a human-readable validation report.
"""

from __future__ import annotations

from typing import List, Dict, Any, Set, Tuple, Optional
from collections import Counter
from datetime import datetime
import json
import os
import re

from backend.pc_element.parser.validator import EngineeringIO
from backend.pc_element.parser.pdf_reader import PageContent


class CompletenessAuditor:
    """Audits extracted I/O sets for completeness and writes a validation report."""

    INVENTORY_PATTERN = re.compile(
        r'''(?ix)
        (?:[-+]?\s*P\s*-?\s*=?\s*|[=+\-]+\s*)?
        (?P<prefix>
            AI800_|AO800_|DI800_|DO800_|
            AI800|AO800|DI800|DO800|
            AICT|DICT|AOC|ACC|AIC|DOC|DIC|
            AI|AO|DI|DO
        )
        \s*_?\s*
        (?P<card>\d{1,4})
        (?:
            \s*\.\s*(?P<channel>\d{1,3})\s*:\s*(?P<terminal>\d{1,4})
          | \s*\.\s*(?P<channel2>\d{1,3})
          | \s*:\s*(?P<port>\d{1,4})
        )?
        \s*/\s*
        (?P<tag>
            [A-Za-z0-9_][A-Za-z0-9_\-]*
            (?:\.[A-Za-z0-9_]+)?
            (?::[A-Za-z0-9_]+)?
        )
        (?![A-Za-z0-9_.])
        '''
    )

    @classmethod
    def inventory_document(cls, pages: List[PageContent]) -> Set[Tuple[str, int, int, str]]:
        """Build ground-truth-like inventory of detectable I/O keys across all text layers."""
        keys: Set[Tuple[str, int, int, str]] = set()
        for page in pages:
            blobs = [page.text, "\n".join(page.raw_lines)]
            for layer in (page.text_layers or {}).values():
                blobs.append(layer)
            for blob in blobs:
                for m in cls.INVENTORY_PATTERN.finditer(blob or ""):
                    prefix = m.group("prefix").upper()
                    if prefix in ("AI800", "AO800", "DI800", "DO800"):
                        prefix = prefix + "_"
                    card = int(m.group("card"))
                    ch = m.group("channel") or m.group("channel2") or m.group("port")
                    channel = int(ch) if ch else 0
                    tag = m.group("tag").upper()
                    keys.add((prefix, card, channel, tag))
        return keys

    @classmethod
    def audit(
        cls,
        pages: List[PageContent],
        extracted: List[EngineeringIO],
        duplicates_removed: int,
        invalid_count: int,
        skipped_candidates: List[str],
    ) -> Dict[str, Any]:
        inventory = cls.inventory_document(pages)
        extracted_keys = {
            (e.io_family.upper(), e.card_number, e.channel_number, e.device_tag.upper())
            for e in extracted
        }

        missing = sorted(inventory - extracted_keys)
        extra = sorted(extracted_keys - inventory)

        cat_counts = Counter(e.category.upper() for e in extracted)
        family_counts = Counter(e.io_family.upper() for e in extracted)

        warnings: List[str] = []
        # Category balance heuristics
        analog_in = cat_counts.get("AI", 0) + cat_counts.get("AI800", 0) + cat_counts.get("AIC", 0)
        analog_out = cat_counts.get("AO", 0) + cat_counts.get("AO800", 0) + cat_counts.get("AOC", 0)
        dig_in = cat_counts.get("DI", 0) + cat_counts.get("DI800", 0) + cat_counts.get("DIC", 0)
        dig_out = cat_counts.get("DO", 0) + cat_counts.get("DO800", 0) + cat_counts.get("DOC", 0)

        if dig_out > 0 and dig_in == 0:
            warnings.append(
                f"Digital outputs detected ({dig_out}) but no digital inputs found in this PDF. "
                "Verify whether DI/DI800 references exist on other sheets or documents."
            )
        if dig_in > 0 and dig_out == 0:
            warnings.append(
                f"Digital inputs detected ({dig_in}) but no digital outputs found in this PDF."
            )
        if analog_out > 0 and analog_in == 0:
            warnings.append(
                f"Analog outputs/config detected ({analog_out}) but no analog inputs found."
            )
        if analog_in > 0 and analog_out == 0:
            warnings.append(
                f"Analog inputs detected ({analog_in}) but no analog outputs/config found."
            )

        # Standard categories expected by Valmet migration workflows
        for expected in ("AI", "AO", "DI", "DO", "AI800", "AO800", "DI800", "DO800"):
            if cat_counts.get(expected, 0) == 0:
                # Only warn for families that also don't appear in inventory
                inv_has = any(
                    k[0].startswith(expected.replace("800", "800")) or k[0] == expected or k[0] == expected + "_"
                    for k in inventory
                )
                if not inv_has and expected in ("DI", "DO", "AO", "AO800", "DI800", "DO800"):
                    warnings.append(
                        f"Category {expected} not present in document text inventory "
                        f"(not a parser miss — reference absent from PDF text layer)."
                    )

        total_inv = len(inventory)
        total_ext = len(extracted_keys)
        matched = len(inventory & extracted_keys)
        accuracy = round((matched / total_inv) * 100.0, 2) if total_inv else 100.0

        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "document_pages": len(pages),
            "inventory_detectable_references": total_inv,
            "extracted_records": total_ext,
            "matched_inventory_records": matched,
            "missing_from_extraction": len(missing),
            "extra_beyond_inventory": len(extra),
            "duplicates_removed": duplicates_removed,
            "invalid_skipped": invalid_count,
            "parser_accuracy_percent": accuracy,
            "category_counts": dict(cat_counts),
            "family_counts": dict(family_counts),
            "balance": {
                "analog_inputs": analog_in,
                "analog_outputs": analog_out,
                "digital_inputs": dig_in,
                "digital_outputs": dig_out,
            },
            "completeness_warnings": warnings,
            "missing_examples": [
                {"family": f, "card": c, "channel": ch, "device_tag": t}
                for f, c, ch, t in missing[:50]
            ],
            "skipped_candidate_examples": skipped_candidates[:30],
            "descriptions_present": sum(1 for e in extracted if (e.description or "").strip()),
            "descriptions_blank": sum(1 for e in extracted if not (e.description or "").strip()),
        }
        return report

    @classmethod
    def write_report(cls, report: Dict[str, Any], output_dir: str, job_id: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"PC_Element_Validation_Report_{job_id}.json")
        txt_path = os.path.join(output_dir, f"PC_Element_Validation_Report_{job_id}.txt")

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)

        lines = [
            "ABB AC450 PC Element — Extraction Validation Report",
            "=" * 60,
            f"Generated: {report.get('generated_at')}",
            f"Document pages: {report.get('document_pages')}",
            "",
            "COUNTS",
            f"  Detectable references in PDF inventory : {report.get('inventory_detectable_references')}",
            f"  Extracted records                      : {report.get('extracted_records')}",
            f"  Matched inventory records              : {report.get('matched_inventory_records')}",
            f"  Missing from extraction                : {report.get('missing_from_extraction')}",
            f"  Duplicates removed                     : {report.get('duplicates_removed')}",
            f"  Invalid skipped                        : {report.get('invalid_skipped')}",
            f"  Parser accuracy                        : {report.get('parser_accuracy_percent')}%",
            "",
            "CATEGORY COUNTS",
        ]
        for k, v in sorted((report.get("category_counts") or {}).items()):
            lines.append(f"  {k}: {v}")

        bal = report.get("balance") or {}
        lines.extend([
            "",
            "I/O BALANCE",
            f"  Analog IN / OUT   : {bal.get('analog_inputs')} / {bal.get('analog_outputs')}",
            f"  Digital IN / OUT  : {bal.get('digital_inputs')} / {bal.get('digital_outputs')}",
            "",
            "DESCRIPTIONS",
            f"  Present : {report.get('descriptions_present')}",
            f"  Blank   : {report.get('descriptions_blank')}",
            "",
            "COMPLETENESS WARNINGS",
        ])
        warns = report.get("completeness_warnings") or []
        if warns:
            for w in warns:
                lines.append(f"  - {w}")
        else:
            lines.append("  (none)")

        miss = report.get("missing_examples") or []
        lines.extend(["", "MISSING EXAMPLES (up to 50)"])
        if miss:
            for m in miss:
                lines.append(
                    f"  {m.get('family')} card={m.get('card')} ch={m.get('channel')} "
                    f"tag={m.get('device_tag')}"
                )
        else:
            lines.append("  (none — extraction covers document inventory)")

        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

        return txt_path
