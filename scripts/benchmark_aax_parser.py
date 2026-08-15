"""
benchmark_aax_parser.py — Run the PC Element pipeline over every AAX file and
report per-file extraction metrics.

Usage:
    python scripts/benchmark_aax_parser.py [--dir <path>] [--json <out>]

Report columns (per file):
    file, bytes, pages, hardwired_ground_truth, records, ai, ao, di, do,
    ai800, ao800, di800, do800, dup_removed, invalid, inv_detectable,
    inv_missing, accuracy_percent, wall_seconds
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.pc_element.parser.parser_service import PCParserService  # noqa: E402

HARDWIRED_RE = re.compile(
    r"=\s*(?P<prefix>AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)"
    r"\s*_?\s*(?P<card>\d{1,4})"
    r"(?:\s*\.\s*(?P<channel>\d{1,3}))?",
    re.IGNORECASE,
)


def read_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def hardwired_ground_truth(text: str) -> Dict[str, int]:
    """Ground truth for HW addresses (unique card.channel per family)."""
    seen: set = set()
    per_family: Dict[str, int] = {}
    for m in HARDWIRED_RE.finditer(text):
        prefix = m.group("prefix").upper()
        if prefix.endswith("800"):
            prefix = prefix + "_"
        card = m.group("card")
        ch = m.group("channel") or "0"
        key = (prefix, card, ch)
        if key in seen:
            continue
        seen.add(key)
        per_family[prefix] = per_family.get(prefix, 0) + 1
    per_family["_total_"] = len(seen)
    return per_family


def bench_one(path: Path) -> Dict[str, Any]:
    text = read_text(path)
    gt = hardwired_ground_truth(text)

    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.perf_counter()
        result = PCParserService(str(path), f"bench_{path.stem}", tmp).execute_pipeline()
        wall = time.perf_counter() - t0

    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "pages": result.total_pages_read,
        "records": result.successfully_parsed,
        "ai": result.ai_count,
        "ao": result.ao_count,
        "di": result.di_count,
        "do": result.do_count,
        "ai800": result.ai800_count,
        "ao800": result.ao800_count,
        "di800": result.di800_count,
        "do800": result.do800_count,
        "other": result.other_count,
        "dup_removed": result.duplicates_removed,
        "invalid": result.invalid_references,
        "inv_detectable": result.inventory_detectable,
        "inv_missing": result.missing_from_inventory,
        "accuracy": result.parser_accuracy_percent,
        "wall_s": round(wall, 2),
        "errors": result.errors,
        "hw_ground_truth": gt,
        "descriptions_found": result.descriptions_found,
        "descriptions_missing": result.descriptions_missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(ROOT / ".AXX Data"))
    parser.add_argument("--json", default="", help="Optional path to write JSON report")
    parser.add_argument("--tag", default="", help="Label for the run (e.g. before/after)")
    parser.add_argument("--pattern", default="*.AAX",
                        help="Glob (default: *.AAX). Use e.g. 23JA1601.AAX to bench one.")
    args = parser.parse_args()

    root = Path(args.dir)
    files = sorted(root.glob(args.pattern))
    if not files:
        # try case-insensitive fallback
        files = sorted(p for p in root.iterdir() if p.suffix.lower() == ".aax")
    if not files:
        print(f"[error] no files match under {root}", file=sys.stderr)
        return 2

    reports: List[Dict[str, Any]] = []
    total_records = 0
    total_gt = 0
    total_time = 0.0

    header = f"{'file':<16} {'B':>7} {'pg':>3} {'rec':>5} {'ai':>4} {'ao':>4} {'di':>4} {'do':>4} {'HWgt':>5} {'inv':>5} {'miss':>5} {'acc%':>6} {'sec':>6}"
    print(header)
    print("-" * len(header))
    for path in files:
        try:
            r = bench_one(path)
        except Exception as exc:  # pragma: no cover
            print(f"{path.name:<16} ERROR {exc}", file=sys.stderr)
            reports.append({"file": path.name, "error": str(exc)})
            continue
        reports.append(r)
        total_records += r["records"]
        total_gt += r["hw_ground_truth"].get("_total_", 0)
        total_time += r["wall_s"]
        print(
            f"{r['file']:<16} {r['bytes']:>7} {r['pages']:>3} {r['records']:>5} "
            f"{r['ai']:>4} {r['ao']:>4} {r['di']:>4} {r['do']:>4} "
            f"{r['hw_ground_truth'].get('_total_', 0):>5} "
            f"{r['inv_detectable']:>5} {r['inv_missing']:>5} "
            f"{r['accuracy']:>6.1f} {r['wall_s']:>6.2f}"
        )

    print("-" * len(header))
    print(f"{'TOTAL':<16} {'':>7} {'':>3} {total_records:>5} "
          f"{'':>4} {'':>4} {'':>4} {'':>4} {total_gt:>5} "
          f"{'':>5} {'':>5} {'':>6} {total_time:>6.2f}")

    if args.json:
        outpath = Path(args.json)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(json.dumps({
            "tag": args.tag,
            "total_records": total_records,
            "total_hw_ground_truth": total_gt,
            "total_wall_seconds": round(total_time, 2),
            "files": reports,
        }, indent=2))
        print(f"\n[saved] {outpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
