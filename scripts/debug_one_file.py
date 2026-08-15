"""Debug helper: print current parser output + a summary of a single AAX file."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.pc_element.parser.parser_service import PCParserService  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: debug_one_file.py <path-to-aax>")
        return 2
    path = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as tmp:
        r = PCParserService(str(path), "debug", tmp).execute_pipeline()

    print(f"records: {r.successfully_parsed}  "
          f"ai={r.ai_count} ao={r.ao_count} di={r.di_count} do={r.do_count}")
    for row in r.preview_data:
        cat = str(row.get("Category") or "")
        card = str(row.get("Slot/Card") or "")
        ch = str(row.get("Channel") or "")
        print(f"  {cat:>6}  {card:>4}  {ch:>4}  {row.get('Device Tag')}")
    print()
    print(f"warnings ({len(r.warnings)}):")
    for w in r.warnings[:30]:
        print(f"  - {w}")

    print()
    text = path.read_bytes().decode("cp1252", errors="replace")
    print(f"--- Raw file candidates for {path.name} ---")
    import re
    for i, ln in enumerate(text.splitlines(), start=1):
        s = ln.strip()
        if not s:
            continue
        # Skip pure numeric parameter lines and comment lines
        if s.startswith("(*"):
            continue
        if re.match(r"^:\d+\s+D=", s):
            continue
        if re.match(r"^:[A-Z_]+\s+D=[\d.E+\-]+$", s):
            continue
        if "=" in s and ("AI" in s.upper() or "AO" in s.upper() or "DI" in s.upper()
                        or "DO" in s.upper() or re.search(r"=\d{2,4}[A-Z]", s)):
            print(f"{i:>4}| {ln}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
