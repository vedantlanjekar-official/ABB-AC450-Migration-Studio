"""
token_assembler.py - Spatial token walk to reconstruct fragmented I/O references.

CAD/vector PDFs often split an address across adjacent glyphs:
  '=' 'AI800_' '22' '.' '5' '/' 'M49FI1201' '.' 'MV'
This assembler walks left-to-right word streams on the same y-band and rebuilds
candidate strings for the grammar parser.
"""

from typing import List, Dict, Any, Set
import re


class TokenAssembler:
    """Rebuilds engineering I/O candidate strings from spatial word tokens."""

    PREFIX_START = re.compile(
        r'(?i)^(?:P-)?=?-?(?:AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|'
        r'AICT|DICT|AOC|ACC|AIC|DOC|DIC|AI|AO|DI|DO)$'
    )
    PREFIX_INLINE = re.compile(
        r'(?i)(?:P-)?=?-?(?:AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|'
        r'AICT|DICT|AOC|ACC|AIC|DOC|DIC|AI|AO|DI|DO)'
    )

    @classmethod
    def assemble_candidates(cls, words: List[Dict[str, Any]]) -> List[str]:
        if not words:
            return []

        # Cluster into horizontal bands
        bands: List[List[Dict[str, Any]]] = []
        for w in sorted(words, key=lambda x: (x.get("top", 0), x.get("x0", 0))):
            placed = False
            y = w.get("top", 0)
            for band in bands:
                if abs(band[0].get("top", 0) - y) <= 4.0:
                    band.append(w)
                    placed = True
                    break
            if not placed:
                bands.append([w])

        candidates: Set[str] = set()
        for band in bands:
            ordered = sorted(band, key=lambda x: x.get("x0", 0))
            # Sliding window join of nearby tokens
            texts = [str(w.get("text", "")).strip() for w in ordered if str(w.get("text", "")).strip()]
            if not texts:
                continue

            # Full band string with and without spaces
            spaced = " ".join(texts)
            glued = "".join(texts)
            for blob in (spaced, glued):
                if "/" in blob and cls.PREFIX_INLINE.search(blob):
                    candidates.add(blob)

            # Grow from each prefix-like token
            for i, tok in enumerate(texts):
                if not (cls.PREFIX_START.match(tok) or cls.PREFIX_INLINE.search(tok) or tok in ("=", "P-", "-P-", "P", "-")):
                    continue
                chunk = tok
                for j in range(i + 1, min(i + 16, len(texts))):
                    nxt = texts[j]
                    # Avoid jumping across large gaps by using simple sequential join
                    if ordered[j].get("x0", 0) - ordered[j - 1].get("x1", 0) > 80:
                        break
                    # Soft-space when both alnum edges meet digits/letters oddly
                    if chunk[-1:].isalnum() and nxt[:1].isalnum() and not (
                        chunk[-1:].isdigit() and nxt[:1].isdigit()
                    ):
                        # keep tight for address fragments like AI800_ + 22
                        if re.search(r'(?i)(AI|AO|DI|DO|AOC|AIC|DOC)$', chunk) and nxt[:1].isdigit():
                            chunk += nxt
                        elif chunk.endswith(("_", ".", ":", "/", "=", "-")) or nxt.startswith((".", ":", "/", "-")):
                            chunk += nxt
                        else:
                            chunk += nxt
                    else:
                        chunk += nxt
                    if "/" in chunk and len(chunk) >= 8:
                        candidates.add(chunk)
                    if len(chunk) > 80:
                        break

        return sorted(c for c in candidates if len(c) >= 8 and "/" in c)
