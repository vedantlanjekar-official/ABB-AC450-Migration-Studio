"""
diff_parser_vs_corpus.py — Corpus-vs-parser gap analysis.

For every AAX file, computes:
  * PARSER SET   : device tags the current parser extracts (via PCParserService)
  * CORPUS SET   : device tags the raw file *looks like* it exposes (broad detection)
  * MISSED       : CORPUS - PARSER (tags the parser misses)
  * EXTRA        : PARSER - CORPUS (tags the parser invents / synthesizes)

The corpus detector is deliberately generous:
  1. `=SOFT.SUFFIX` where SUFFIX is a known engineering suffix
  2. `=SOFT:SUFFIX` where SUFFIX is a known engineering suffix
  3. any hardwired I/O address `=AI7.10` etc.
  4. block :DBINST provides an implicit device tag when the block wires HW addresses

Usage:
    python scripts/diff_parser_vs_corpus.py [--dir <path>] [--files <file1> <file2> ...]
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.pc_element.parser.parser_service import PCParserService  # noqa: E402
from backend.pc_element.parser.aax_reader import _SUFFIX_CATEGORY  # noqa: E402

HARDWIRED_RE = re.compile(
    r"=\s*(?P<prefix>AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)"
    r"\s*_?\s*(?P<card>\d{1,4})"
    r"(?:\s*\.\s*(?P<channel>\d{1,3}))?",
    re.IGNORECASE,
)
SOFT_DOT_RE = re.compile(
    r"=\s*(?P<tag>(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"[0-9]{2,4}[A-Za-z][0-9A-Za-z_\-]*"
    r"(?:\.[0-9A-Za-z_]+)+)",
    re.IGNORECASE,
)
SOFT_COLON_RE = re.compile(
    r"=\s*(?P<base>(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"[0-9]{2,4}[A-Za-z][0-9A-Za-z_\-]*)"
    r"\s*:\s*(?P<suf>[A-Za-z][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
NUMERIC_RE = re.compile(r"^[\d.]+E?[+\-]?\d*$", re.IGNORECASE)


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


def corpus_device_tags(text: str) -> Set[str]:
    """Best-effort set of device tags this file plausibly exposes."""
    tags: Set[str] = set()

    for m in HARDWIRED_RE.finditer(text):
        prefix = m.group("prefix").upper()
        if prefix.endswith("800"):
            prefix += "_"
        addr = f"{prefix}{m.group('card')}"
        if m.group("channel"):
            addr = f"{addr}.{m.group('channel')}"
        tags.add(addr)

    for m in SOFT_DOT_RE.finditer(text):
        tag = m.group("tag").upper()
        # Reject pure-number fragments (10.000000E, 122T124A.B1 also passes but
        # is a DAT reference — keep, mark with prefix so we can filter later)
        if NUMERIC_RE.match(tag):
            continue
        suffix = tag.rsplit(".", 1)[-1]
        if suffix in _SUFFIX_CATEGORY:
            tags.add(tag)

    for m in SOFT_COLON_RE.finditer(text):
        base = m.group("base").upper()
        suf = m.group("suf").upper()
        if suf in _SUFFIX_CATEGORY:
            tags.add(f"{base}.{suf}")

    return tags


def parser_device_tags(path: Path) -> Tuple[Set[str], Dict[str, int]]:
    with tempfile.TemporaryDirectory() as tmp:
        result = PCParserService(str(path), f"diff_{path.stem}", tmp).execute_pipeline()

    tags = {row.get("Device Tag", "").upper() for row in result.preview_data}
    counts = {
        "records": result.successfully_parsed,
        "ai": result.ai_count,
        "ao": result.ao_count,
        "di": result.di_count,
        "do": result.do_count,
        "ai800": result.ai800_count,
        "ao800": result.ao800_count,
        "di800": result.di800_count,
        "do800": result.do800_count,
    }
    return tags, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(ROOT / ".AXX Data"))
    parser.add_argument("--files", nargs="*", default=[],
                        help="Optional subset of filenames (relative to --dir)")
    parser.add_argument("--limit-missing", type=int, default=20)
    args = parser.parse_args()

    root = Path(args.dir)
    files = ([root / f for f in args.files]
             if args.files
             else sorted(root.glob("*.AAX")))

    grand_corpus = 0
    grand_parser = 0
    grand_missed = 0
    grand_extra = 0

    for path in files:
        text = read_text(path)
        corpus = corpus_device_tags(text)
        try:
            parser_tags, counts = parser_device_tags(path)
        except Exception as exc:
            print(f"{path.name} ERROR {exc}")
            continue

        # Ignore parser tags that are HW addresses (they aren't in the corpus set)
        parser_tags_clean = {t for t in parser_tags if t}
        missed = corpus - parser_tags_clean
        extra = parser_tags_clean - corpus

        grand_corpus += len(corpus)
        grand_parser += len(parser_tags_clean)
        grand_missed += len(missed)
        grand_extra += len(extra)

        head = (
            f"{path.name:<16}  corpus={len(corpus):>3}  parser={len(parser_tags_clean):>3}  "
            f"missed={len(missed):>3}  extra={len(extra):>3}  records={counts['records']:>3}"
        )
        print(head)
        if missed:
            preview = sorted(missed)[: args.limit_missing]
            print("   missed:  " + ", ".join(preview))
        if extra and len(extra) <= args.limit_missing:
            print("   extra :  " + ", ".join(sorted(extra)))

    print()
    print(f"TOTAL corpus={grand_corpus} parser={grand_parser} "
          f"missed={grand_missed} extra={grand_extra}")
    if grand_corpus:
        recall = 100.0 * (grand_corpus - grand_missed) / grand_corpus
        print(f"recall vs broad corpus: {recall:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
