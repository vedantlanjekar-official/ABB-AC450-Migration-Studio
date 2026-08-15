"""
analyze_aax_corpus.py — Corpus-level structural analysis for the ABB AC450 AAX dataset.

Iterates every .AAX file under a directory (default: ./.AXX Data), reads the raw text,
and reports the recurring engineering patterns needed to redesign the parser.

Usage:
    python scripts/analyze_aax_corpus.py [--dir "<path>"]

Output is a JSON report on stdout plus per-file summaries. Nothing is written to disk.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / ".AXX Data"


HARDWIRED_RE = re.compile(
    r"=\s*(?P<prefix>AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)"
    r"\s*_?\s*(?P<card>\d{1,4})"
    r"(?:\s*\.\s*(?P<channel>\d{1,3}))?"
    r"(?:\s*:\s*(?P<attr>[A-Za-z0-9_]+))?",
    re.IGNORECASE,
)

SOFT_DOT_RE = re.compile(
    r"=\s*(?P<tag>(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"[0-9A-Za-z][0-9A-Za-z_\-]*(?:\.[0-9A-Za-z_]+)+)",
    re.IGNORECASE,
)

SOFT_COLON_RE = re.compile(
    r"=\s*(?P<base>(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"[0-9]{2,4}[A-Za-z][0-9A-Za-z_\-]*)"
    r"\s*:\s*(?P<suf>[A-Za-z][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

PARAM_LINE_RE = re.compile(r"^\s*:(?P<param>[A-Za-z0-9_]+)\s*(?P<body>.*)$")
DBINST_RE = re.compile(r":DBINST\s*=?\s*(?:=)?\s*(?P<tag>[A-Za-z0-9_][A-Za-z0-9_\-.]*)")

OBJECT_HEADER_RE = re.compile(
    r"^(?P<id>PC\d+(?:\.\d+)*)\s+(?P<block>[A-Za-z][A-Za-z0-9_\-]*)\b"
)

FUNCTION_BLOCKS = {"PIDCON", "MOTCON", "VALVECON", "MANSTN", "RATIOSTN", "CONTRM"}
PAGE_TITLE_RE = re.compile(
    r'^"\s*(?:(?P<tag>[0-9]{2,4}[A-Za-z]{1,4}[0-9A-Za-z_]*)\s*:\s*)?(?P<desc>[^"]+)"\s*$'
)

PAGE_SPLIT_RE = re.compile(r"^PCD-PAGE(?:\s+(\d+))?\s*$", re.IGNORECASE | re.MULTILINE)


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


def analyze_file(path: Path) -> Dict[str, Any]:
    text = read_text(path)

    pages = PAGE_SPLIT_RE.findall(text)
    total_pages = len(pages)

    hardwired: Counter = Counter()
    hardwired_examples: List[str] = []
    soft_suffixes: Counter = Counter()
    soft_examples: List[str] = []
    colon_suffixes: Counter = Counter()
    colon_examples: List[str] = []
    params_with_io: Counter = Counter()
    block_types: Counter = Counter()
    dbinst_tags: List[str] = []
    page_titles: List[str] = []
    lines_with_leading_equals_only: Counter = Counter()

    total_lines = 0
    for raw_line in text.splitlines():
        total_lines += 1
        stripped = raw_line.strip()

        oh = OBJECT_HEADER_RE.match(stripped)
        if oh:
            block_types[oh.group("block").upper()] += 1

        db = DBINST_RE.search(stripped)
        if db:
            dbinst_tags.append(db.group("tag"))

        pt = PAGE_TITLE_RE.match(stripped)
        if pt:
            page_titles.append(pt.group("desc"))

        param_name = ""
        body = stripped
        pm = PARAM_LINE_RE.match(stripped)
        if pm:
            param_name = pm.group("param").upper()
            body = pm.group("body")

        hw_hits = list(HARDWIRED_RE.finditer(body))
        for m in hw_hits:
            prefix = m.group("prefix").upper()
            if prefix.endswith("800"):
                prefix += "_"
            hardwired[prefix] += 1
            if len(hardwired_examples) < 20:
                hardwired_examples.append(stripped[:160])
            if param_name:
                params_with_io[param_name] += 1

        for m in SOFT_DOT_RE.finditer(body):
            tag = m.group("tag")
            if "." in tag:
                suffix = tag.rsplit(".", 1)[-1].upper()
                soft_suffixes[suffix] += 1
                if len(soft_examples) < 30:
                    soft_examples.append(f"{tag}  << {stripped[:100]}")

        for m in SOFT_COLON_RE.finditer(body):
            suf = m.group("suf").upper()
            colon_suffixes[suf] += 1
            if len(colon_examples) < 30:
                colon_examples.append(f"{m.group('base')}:{suf}  << {stripped[:100]}")

        # Continuation lines that begin with '=' (attribute wrapping)
        if stripped.startswith("=") and not stripped.startswith("=="):
            lines_with_leading_equals_only[stripped[:6]] += 1

    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "total_lines": total_lines,
        "pcd_pages": total_pages,
        "hardwired_by_family": dict(hardwired),
        "hardwired_total": sum(hardwired.values()),
        "hardwired_examples": hardwired_examples,
        "soft_dot_suffixes_top": dict(soft_suffixes.most_common(20)),
        "soft_dot_total": sum(soft_suffixes.values()),
        "soft_dot_examples": soft_examples[:10],
        "colon_suffixes_top": dict(colon_suffixes.most_common(20)),
        "colon_total": sum(colon_suffixes.values()),
        "colon_examples": colon_examples[:10],
        "io_params_top": dict(params_with_io.most_common(15)),
        "block_types_top": dict(block_types.most_common(15)),
        "dbinst_count": len(dbinst_tags),
        "dbinst_sample": dbinst_tags[:15],
        "page_titles_sample": page_titles[:10],
    }


def summarise_corpus(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    hardwired_totals: Counter = Counter()
    soft_totals: Counter = Counter()
    colon_totals: Counter = Counter()
    io_param_totals: Counter = Counter()
    block_totals: Counter = Counter()

    for r in reports:
        for family, count in r["hardwired_by_family"].items():
            hardwired_totals[family] += count
        for suffix, count in r["soft_dot_suffixes_top"].items():
            soft_totals[suffix] += count
        for suffix, count in r["colon_suffixes_top"].items():
            colon_totals[suffix] += count
        for param, count in r["io_params_top"].items():
            io_param_totals[param] += count
        for block, count in r["block_types_top"].items():
            block_totals[block] += count

    return {
        "files_analyzed": len(reports),
        "hardwired_total_by_family": dict(hardwired_totals),
        "hardwired_grand_total": sum(hardwired_totals.values()),
        "soft_dot_suffix_top50": dict(soft_totals.most_common(50)),
        "colon_suffix_top50": dict(colon_totals.most_common(50)),
        "io_params_top30": dict(io_param_totals.most_common(30)),
        "block_types_top20": dict(block_totals.most_common(20)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(DEFAULT_DIR),
                        help="Directory containing .AAX files")
    parser.add_argument("--per-file", action="store_true",
                        help="Include per-file detail in the JSON output")
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists():
        print(f"[error] directory not found: {root}", file=sys.stderr)
        return 2

    aax_files = sorted(root.glob("*.AAX")) + sorted(root.glob("*.aax"))
    if not aax_files:
        print(f"[error] no .AAX files under: {root}", file=sys.stderr)
        return 2

    reports = [analyze_file(p) for p in aax_files]
    summary = summarise_corpus(reports)

    payload = {
        "root": str(root),
        "summary": summary,
    }
    if args.per_file:
        payload["per_file"] = reports

    print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
