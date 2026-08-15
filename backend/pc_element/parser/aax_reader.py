"""
aax_reader.py — Multi-stage ABB AC450 AAX extraction engine.

Public interface (unchanged, drop-in compatible):

    AaxReader(file_path).read_all_pages() -> List[PageContent]

The reader produces synthesized candidate lines of the form

    =CAT{card}.{ch}/DeviceTag        (hardwired address, card >= 1)
    =CAT0.0/DeviceTag                (soft device tag, no hardwired address)

which the existing PC Element pipeline (IOReferenceDetector, GrammarParser,
DescriptionMapper, Validator, RecordClubber, ExcelGenerator) consumes without
modification.

────────────────────────────────────────────────────────────────────────────
Extraction pipeline (each stage is independent and idempotent):

  Stage 0  Encoding      : bytes → text (utf-8-sig, utf-8, cp1252, latin-1)
  Stage 1  Header meta   : first 80 lines → {IEC_*, R_Text*, Design_ch, …}
  Stage 2  Page split    : text → List[PageBlob] via ``PCD-PAGE`` markers
  Stage 3  Block segment : PageBlob → List[Block] (object header + :param
                           lines), with continuation-line join and comment
                           stripping. Continuation = param line ending with
                           ``,`` joins the next non-empty body.
  Stage 4  Extraction (per Block, results merged into a priority-keyed set)
    4A  Hardwired I/O            (=AI7.10, =DI2.23:BLOCKED, whitespace-safe)
    4B  Soft dotted device tag   (=82PIC972.MV, =82HSV974.SV, …)
    4C  Colon-form soft tag      (=82LIC428:BLK_D → 82LIC428.BLK_D)
    4D  Block-context resolution (PIDCON/MOTCON/VALVECON :DBINST + :MV → HW)
    4E  Continuation reference   (\\n-broken =AO3.9 pairs)
    4F  PCU-I / PCU-O            (:IOADDR + :CHANNEL → Slot/Card + Channel)
    4G  Address join             (MOVE port pairs + named FB params → plant tag)
  Stage 5  Global fallback       : whole-text rescan for anything Stage 4 missed
  Stage 6  Validation warnings   : unmapped suffixes, absent categories, HW gaps

Design principles:

  * Every stage operates on the same normalised ``Block`` graph, so a change
    to any single pattern cannot silently corrupt other stages.
  * Extraction is generous first, then filtered: we prefer to emit a candidate
    with a low priority than to skip it silently.
  * Priority merge: hardwired evidence (Stage 4A / 4D / 5) always wins over
    soft evidence for the same physical channel.
  * Every skipped candidate that looked like I/O is recorded on
    ``AaxReader.warnings`` for the completeness auditor.
  * Business logic downstream is untouched.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from backend.pc_element.parser.pdf_reader import PageContent

logger = logging.getLogger("pc_element_parser")


# ──────────────────────────────────────────────────────────────────────────
# Regexes (compile once; keep ReDoS-safe: no nested `*` on tag body)
# ──────────────────────────────────────────────────────────────────────────

_PAGE_SPLIT = re.compile(r"^PCD-PAGE(?:\s+(\d+))?\s*$", re.IGNORECASE | re.MULTILINE)

_COMMENT_BLOCK = re.compile(r"\(\*.*?\*\)", re.DOTALL)

_OBJECT_HEADER = re.compile(
    r"^\s*(?P<id>PC\d+(?:\.\d+)*)\s+(?P<block>[A-Za-z][A-Za-z0-9_\-]*)\b",
    re.IGNORECASE,
)

_PAGE_TITLE = re.compile(
    r'^"\s*(?:(?P<tag>[0-9]{2,4}[A-Za-z]{1,4}[0-9A-Za-z_]*)\s*:\s*)?'
    r'(?P<desc>[^"]+)"\s*$'
)

_PARAM_LINE = re.compile(
    r"^\s*:(?P<param>[A-Za-z0-9_=<>]+)\s*(?P<body>.*)$",
    re.IGNORECASE,
)

_DBINST_ANY = re.compile(
    r":DBINST\s+=?\s*(?P<tag>[A-Za-z0-9_][A-Za-z0-9_\-.]*)",
    re.IGNORECASE,
)

_HEADER_FIELD = re.compile(
    r"^\s*(?P<key>IEC_[A-Za-z0-9_]+|R_Text\d+|Design_ch|Tech_ref|Resp_dept|Language|Rev_Ind|Date)"
    r"\s+(?P<val>.+?)\s*$",
    re.IGNORECASE,
)

_N_SIGNAL = re.compile(r"N=\((?P<name>[^)]+)\)", re.IGNORECASE)

# Hardwired addressing (whitespace-tolerant) — captures :ATTR when present
_IO_HW = re.compile(
    r"=\s*(?P<prefix>AI800_|AO800_|DI800_|DO800_|AI800|AO800|DI800|DO800|AI|AO|DI|DO)"
    r"\s*_?\s*(?P<card>\d{1,4})"
    r"(?:\s*\.\s*(?P<channel>\d{1,3}))?"
    r"(?:\s*:\s*(?P<attr>[A-Za-z0-9_]+))?",
    re.IGNORECASE,
)

# Soft device tag with at least one .SUFFIX (excludes AI/AO/DI/DO hardwired forms)
_SOFT_DOTTED = re.compile(
    r"=\s*(?P<tag>"
    r"(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"[0-9A-Za-z][0-9A-Za-z_\-]*"
    r"(?:\.[0-9A-Za-z_]+)+"
    r")"
    r"(?:\s*:\s*(?P<attr>[A-Za-z0-9_]+))?",
    re.IGNORECASE,
)

# Colon-form soft attribute (=82LIC428:BLK_D → 82LIC428.BLK_D)
_SOFT_COLON = re.compile(
    r"=\s*(?P<base>"
    r"(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"[0-9]{2,4}[A-Za-z][0-9A-Za-z_\-]*"
    r")"
    r"\s*:\s*(?P<suf>[A-Za-z][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

# Plant tag on I/O param (may be bare loop tag — allows :MV =82PIC972)
_PLANT_ON_IO_PARAM = re.compile(
    r"=\s*(?P<tag>"
    r"(?!(?:AI|AO|DI|DO)(?:800_?)?\d)"
    r"(?!\d+[Ee][+\-]?\d)"          # not scientific notation fragment
    r"[0-9A-Za-z][0-9A-Za-z_\-]*(?:\.[0-9A-Za-z_]+)*"
    r")"
    r"(?:\s*:\s*[A-Za-z0-9_]+)?",
    re.IGNORECASE,
)

# DAT-array / config suffix filter: reject `.B1`, `.R14`, `.R1R`, `.B1S`, `.R10S`
_DAT_ARRAY_SUFFIX = re.compile(r"^[BR]\d+[RS]?$|^COM$|^CONFIG\d*$|^COST$|^MWHT$|^TOTAL$", re.IGNORECASE)

_NUMERICISH = re.compile(r"^[\d.E+\-]+$", re.IGNORECASE)
_SCIENTIFIC = re.compile(r"^[\d.]+E\d*$", re.IGNORECASE)
_SKIP_PREFIXES = ("APMR.", "MMC_X.", "DAT(", "PC")


# ──────────────────────────────────────────────────────────────────────────
# Suffix catalog (derived from full corpus analysis of PM2/PM3 AAX exports)
#
# Each suffix maps to the target I/O category. Adding a new suffix is a
# one-line addition here — no other change required.
# ──────────────────────────────────────────────────────────────────────────

_SUFFIX_CATEGORY: Dict[str, str] = {
    # ── Analog inputs ────────────────────────────────────────────────
    "MV": "AI", "PV": "AI", "IT": "AI", "IT_": "AI",
    "MEAS": "AI", "CURR": "AI", "AI": "AI",
    "DIA": "AI", "TRGT": "AI", "FLO": "AI", "ZI": "AI",
    "HICURR": "AI", "MC": "AI", "WSP": "AI", "SP": "AI",
    "SSP": "AI", "SSP_": "AI",       # speed set point / raw
    "CSP": "AI", "CSP_": "AI",       # commanded set point / raw
    "SETP": "AI",
    "NOM_CURR": "AI", "HHYS": "AI",
    "PIL": "AI",                     # pressure interlock / analog signal
    "IN": "AI",                      # analog input (soft label)
    "SPEEDMV": "AI",                 # speed measurement value (PCU-I derived)
    "CALC_VAL": "AI",
    "MWHT": "AI",
    "COST": "AI",
    "TOTAL": "AI",
    "VALUE": "AI",
    "PULSEOUT": "DO",

    # ── Analog outputs ───────────────────────────────────────────────
    "OUT": "AO", "POUT": "AO", "CO": "AO", "AO": "AO",
    "OUTA": "AO", "OUTB": "AO", "OP": "AO",
    "OUTP": "AO", "OUTPH": "AO", "OUTPL": "AO",

    # ── Digital outputs / valve / motor command ──────────────────────
    "SV": "DO", "SV1": "DO", "SVA": "DO", "SVB": "DO",
    "SVD": "DO", "SVU": "DO", "SBU": "DO", "CMD": "DO",
    "MSTR": "DO", "START": "DO", "STOP": "DO",
    "SO1": "DO", "SO2": "DO", "DO": "DO",
    "CLS": "DO", "OPN": "DO", "OPNL": "DO",
    "SON": "DO", "SOF": "DO",

    # ── Digital inputs / status / limits ─────────────────────────────
    "RUN": "DI", "FLT": "DI", "FAULT": "DI",
    "OPEN": "DI", "CLOSE": "DI", "CLOSED": "DI",
    "ZS": "DI", "ZSD": "DI", "ZSU": "DI", "ZSC": "DI",
    "RDY": "DI", "READY": "DI", "SEL": "DI", "SELECTED": "DI",
    "ESTOP": "DI",
    "PSH": "DI", "PSL": "DI", "FSL": "DI", "FSH": "DI",
    "ST": "DI", "STS": "DI", "STF": "DI", "ST_": "DI",
    "DI": "DI", "OFF": "DI", "ON": "DI",
    "CRWL": "DI", "INCH": "DI",
    "DUTY": "DI", "TANDM": "DI", "INDIV": "DI",
    "SUND": "DI", "LSTA": "DI", "LSTP": "DI",
    "KEY": "DI", "LDN": "DI", "LUP": "DI", "LRF": "DI",
    "INT": "DI", "INT_": "DI",
    "FWD": "DI", "SFWD": "DI",
    "FLUSH": "DI", "VIL": "DI", "VIL1": "DI", "VIL2": "DI",
    "ALM": "DI", "ALM1": "DI", "ALM2": "DI",
    "LSH": "DI", "LSL": "DI",
    "TSH": "DI", "VSH": "DI", "MIL": "DI", "ZIL": "DI",
    "AUT": "DI", "JOG": "DI", "OK": "DI",
    "INC": "DI", "DEC": "DI", "CINC": "DI", "CDEC": "DI",
    "GST": "DI", "FES": "DI", "SET": "DI",
    "TLOW": "DI", "TRUN": "DI",
    "SS": "DI", "SI": "DI", "SM": "DI", "SQ": "DI",
    "VENT": "DI", "TMR": "DI",
    "CZ": "DI", "BUL": "DI", "AIL": "DI",
    "STIM": "DI", "ETIM": "DI",
    "AS1": "DI", "AS2": "DI", "AS3": "DI", "AS4": "DI",
    "AS5": "DI", "AS6": "DI",
    "FSA1": "DI", "FSA2": "DI",
    "ERR": "DI", "M2": "DI", "RFS": "DI",
    "WUP": "DI",                     # warm-up interlock
    "MWHT": "DI",                    # deliberately not classified? See filter list.

    # ── Colon-form soft DB attributes seen in AAX exports ────────────
    "BLK_D": "DI", "BLK_I": "DI", "VALID": "DI", "MORD": "DI",
}

# Colon attributes that are FB parameter dumps, not field I/O.
_SKIP_COLON_ATTR = re.compile(
    r"^(?:PARAM\d*[A-Z]?|PC_PARM|PC_RES|REAL[A-Z]*|BOOL[A-Z]*|"
    r"HI_LIM\d*|LO_LIM\d*|RANGE(?:MAX|MIN)|NOM_CURR)$",
    re.IGNORECASE,
)

# FB / connection parameter → preferred category + Device Tag suffix
_PARAM_HINT: Dict[str, Tuple[str, str]] = {
    "MV": ("AI", "MV"),
    "ALCBLK": ("AI", "ERR"),
    "OUTP": ("AO", "OUT"),
    "OUT": ("AO", "OUT"),
    "POUT": ("AO", "OUT"),
    "CLS": ("DO", "CLS"),
    "OPN": ("DO", "OPN"),
    "OPNL": ("DO", "OPN"),
    "SO1": ("DO", "SO1"),
    "SO2": ("DO", "SO2"),
    "I": ("AI", "IN"),
    "I1": ("AI", "IN"),
    "MC": ("AI", "MC"),
    "M2": ("DI", "M2"),
    "RFS": ("DI", "RFS"),
    "CMD": ("DO", "CMD"),
    "SV": ("DO", "SV"),
    "WSP": ("AI", "WSP"),
    "DEV": ("DI", "DEV"),
    "MAN": ("DI", "MAN"),
    "AUTO": ("DI", "AUT"),
    "TRACKA": ("AI", "MV"),
    "TRACKB": ("AI", "MV"),
    "BAL": ("AO", "OUT"),
    "SP": ("AI", "SP"),
    "SPEEDMV": ("AI", "SPEEDMV"),
    "SPEEDSF": ("AI", "SPEEDMV"),
}

# Named FB ports whose HW assignment is unambiguous (beats generic :I / :21)
_STRONG_IO_PARAMS: Set[str] = {
    "MV", "MC", "SO1", "SO2", "CLS", "OPN", "OPNL",
    "M2", "CMD", "SV", "POUT", "OUTP", "OUT",
}

# Params that imply a plant I/O connection even for bare tags
_IO_PARAMS: Set[str] = set(_PARAM_HINT.keys())


# ──────────────────────────────────────────────────────────────────────────
# Internal data model
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class _ParamLine:
    """A single ``:PARAM value`` line inside an object block."""
    name: str
    body: str
    raw: str
    line_no: int


@dataclass
class _Block:
    """An object block: header + attached parameter lines."""
    obj_id: str
    block_type: str
    page_number: int
    title_tag: str
    params: List[_ParamLine] = field(default_factory=list)

    @property
    def dbinst(self) -> str:
        for p in self.params:
            m = _DBINST_ANY.search(f":{p.name} {p.body}")
            if m:
                return _clean_tag(m.group("tag"))
        return ""


@dataclass
class _Candidate:
    """A synthesized I/O candidate ready for emission."""
    addr: str            # e.g. 'AI7.10' or 'AI0.0' for soft-only
    device_tag: str      # e.g. '82PIC972.MV'
    category: str        # 'AI' | 'AO' | 'DI' | 'DO' | 'AI800' | ...
    priority: int        # higher = stronger evidence
    hardwired: bool
    source: str          # short human-readable origin


# ──────────────────────────────────────────────────────────────────────────
# Tag cleaning + validation (AAX-side; downstream keeps its own cleaner)
# ──────────────────────────────────────────────────────────────────────────

def _clean_tag(raw: str) -> str:
    """Normalize a device-tag-like string. Preserves trailing ``_`` suffixes."""
    tag = (raw or "").strip().upper().lstrip("=")
    if not tag:
        return ""
    if ":" in tag:
        tag = tag.split(":", 1)[0]
    tag = tag.strip().rstrip(".,; ")
    m = re.match(r"^([A-Z0-9][A-Z0-9_\-]*(?:\.[A-Z0-9_\-]*)*)", tag)
    if not m:
        return tag
    # Preserve trailing underscores (IT_, ST_, INT_, SSP_ are legitimate ABB
    # suffixes and MUST NOT be collapsed with the underscore-less variants).
    return m.group(1).rstrip(".-")


_PLANT_BASE_RE = re.compile(r"^[A-Z]?\d{2,4}[A-Z][A-Z0-9_]*$", re.IGNORECASE)


def _looks_like_plant_base(base: str) -> bool:
    """A plant tag base needs ≥ 2 consecutive digits after an optional single
    leading letter (e.g. 82PIC972, X82F521, M49FI1201, 122F124A). Short bases
    like ``H1`` or ``L1`` are rejected."""
    if not base or len(base) < 4:
        return False
    return bool(_PLANT_BASE_RE.match(base))


def _is_valid_tag(tag: str, *, allow_hw_addr: bool = False) -> bool:
    """Keep every plant-looking AAX tag so Excel receives the full I/O set.

    Reject only numeric literals, scientific fragments, and known non-I/O
    prefixes (APMR / MMC_X / PC internals). Unmapped suffixes such as DAT
    slots (.B1, .R2, .R1R) are kept when the base looks like a plant tag.
    """
    if not tag or len(tag) < 3 or not re.search(r"[A-Z]", tag):
        return False
    upper = tag.upper()
    if allow_hw_addr and re.match(
        r"^(?:AI|AO|DI|DO)(?:800_?)?\d+(?:\.\d+)?$", upper
    ):
        return True
    if _NUMERICISH.match(tag.replace(".", "")):
        return False
    if _SCIENTIFIC.match(tag) or re.match(r"^[\d.]+$", tag):
        return False
    if upper.startswith(_SKIP_PREFIXES):
        return False
    if "." in tag:
        suf = tag.rsplit(".", 1)[-1].upper()
        if suf.isdigit():
            return False
        base = tag.rsplit(".", 1)[0]
        if suf in _SUFFIX_CATEGORY:
            return _looks_like_plant_base(base)
        if not re.match(r"^[A-Z][A-Z0-9_]*$", suf):
            return False
        return _looks_like_plant_base(base)
    return _looks_like_plant_base(tag)


def _category_from_tag(tag: str) -> str:
    if "." not in tag:
        return ""
    suffix = tag.rsplit(".", 1)[-1].upper()
    return _SUFFIX_CATEGORY.get(suffix, "")


def _normalise_prefix(prefix: str) -> Tuple[str, str]:
    """Return (canonical family, category code) for a raw prefix like AI800 or AI800_."""
    p = prefix.upper()
    if p in ("AI800", "AI800_"):
        return "AI800_", "AI800"
    if p in ("AO800", "AO800_"):
        return "AO800_", "AO800"
    if p in ("DI800", "DI800_"):
        return "DI800_", "DI800"
    if p in ("DO800", "DO800_"):
        return "DO800_", "DO800"
    return p, p


def _load_text(path: Path) -> str:
    """Robust decoder: BOM → utf-8-sig, then utf-8, cp1252, latin-1."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _extract_header_metadata(text: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    head = "\n".join(text.splitlines()[:80])
    for m in _HEADER_FIELD.finditer(head):
        key = m.group("key").strip()
        val = m.group("val").strip()
        if val and key not in meta:
            meta[key] = val
    return meta


# ──────────────────────────────────────────────────────────────────────────
# Stage 3 — block segmentation with continuation join
# ──────────────────────────────────────────────────────────────────────────

def _segment_blocks(
    page_number: int, title_tag: str, page_lines: List[str]
) -> Tuple[List[_Block], List[_ParamLine]]:
    """Split a page's substantive lines into object blocks + orphan params.

    Continuation join: any :param body ending with ``,`` absorbs the next
    non-empty continuation line (leading whitespace + no ``:PARAM`` header).
    """
    blocks: List[_Block] = []
    orphan_params: List[_ParamLine] = []
    current: Optional[_Block] = None

    i = 0
    total = len(page_lines)
    while i < total:
        raw = page_lines[i]
        stripped = raw.strip()

        if not stripped:
            i += 1
            continue

        header = _OBJECT_HEADER.match(stripped)
        if header:
            current = _Block(
                obj_id=header.group("id"),
                block_type=header.group("block").upper(),
                page_number=page_number,
                title_tag=title_tag,
            )
            blocks.append(current)
            i += 1
            continue

        pm = _PARAM_LINE.match(stripped)
        if pm:
            name = pm.group("param").upper()
            body = pm.group("body") or ""
            # Continuation join
            while body.rstrip().endswith(",") and i + 1 < total:
                nxt = page_lines[i + 1]
                nxt_stripped = nxt.strip()
                if not nxt_stripped or _PARAM_LINE.match(nxt_stripped) or _OBJECT_HEADER.match(nxt_stripped):
                    break
                body = body.rstrip().rstrip(",") + " " + nxt_stripped
                i += 1
            param = _ParamLine(name=name, body=body, raw=stripped, line_no=i)
            if current is not None:
                current.params.append(param)
            else:
                orphan_params.append(param)
            i += 1
            continue

        # Non-header, non-param line — attach as a synthetic param so
        # references in free-standing wire text are still scanned.
        if current is not None:
            current.params.append(
                _ParamLine(name="_WIRE_", body=stripped, raw=stripped, line_no=i)
            )
        else:
            orphan_params.append(
                _ParamLine(name="_WIRE_", body=stripped, raw=stripped, line_no=i)
            )
        i += 1

    return blocks, orphan_params


# ──────────────────────────────────────────────────────────────────────────
# Stage 4 — extraction passes
# ──────────────────────────────────────────────────────────────────────────

class _CandidateSet:
    """Priority-keyed I/O candidate accumulator."""

    def __init__(self) -> None:
        self._by_key: Dict[str, _Candidate] = {}
        self.skipped: List[str] = []

    def add(self, cand: _Candidate, *, skip_reason: str = "") -> bool:
        """Insert cand if it is stronger evidence than any existing entry.

        Returns True when accepted, False when rejected (with skip_reason
        recorded when non-empty).
        """
        if not cand.device_tag:
            if skip_reason:
                self.skipped.append(skip_reason)
            return False

        # Validate tag body (HW addresses tolerated when they *are* the tag)
        if not _is_valid_tag(cand.device_tag, allow_hw_addr=True):
            if skip_reason:
                self.skipped.append(skip_reason)
            return False

        if cand.hardwired:
            key = f"HW:{cand.addr.upper()}"
            # Hardwired always wins over previous soft entry for the same tag
            self._by_key.pop(f"SOFT:{cand.device_tag.upper()}", None)
            existing = self._by_key.get(key)
            if existing is None or cand.priority > existing.priority:
                self._by_key[key] = cand
                return True
            return False

        # Soft candidate
        key = f"SOFT:{cand.device_tag.upper()}"
        # If a hardwired entry already owns this tag, prefer the HW form.
        for k, v in list(self._by_key.items()):
            if k.startswith("HW:") and v.device_tag.upper() == cand.device_tag.upper():
                return False
        existing = self._by_key.get(key)
        if existing is None or cand.priority > existing.priority:
            self._by_key[key] = cand
            return True
        return False

    def hw_addresses(self) -> Set[str]:
        return {k[3:] for k in self._by_key if k.startswith("HW:")}

    def emit_lines(self) -> List[str]:
        return [
            f"={c.addr}/{c.device_tag}"
            for c in self._by_key.values()
        ]

    def attach_address(
        self,
        device_tag: str,
        addr: str,
        category: str,
        *,
        priority: int,
        source: str,
    ) -> None:
        """Copy a resolved card.channel onto a plant tag without collapsing
        other tags that share the same physical address.

        Soft rows stay keyed by device tag (SOFT:TAG) so ``82PIC972.POUT`` and
        ``82PIC972.OUT`` can both carry ``AO3.9``.
        """
        if not device_tag or not addr or not _is_valid_tag(device_tag):
            return
        tag_key = f"SOFT:{device_tag.upper()}"
        existing = self._by_key.get(tag_key)
        if existing is None:
            for cand in self._by_key.values():
                if cand.device_tag.upper() == device_tag.upper():
                    existing = cand
                    break
        if existing is not None:
            if existing.hardwired and existing.priority > priority:
                return
            existing.addr = addr
            existing.category = category
            existing.hardwired = True
            existing.priority = max(existing.priority, priority)
            existing.source = source
            return
        self.add(
            _Candidate(
                addr=addr,
                device_tag=device_tag,
                category=category,
                priority=priority,
                hardwired=False,
                source=source,
            )
        )
        existing = self._by_key.get(tag_key)
        if existing is not None:
            existing.addr = addr
            existing.hardwired = True
            existing.priority = max(existing.priority, priority)
            existing.source = source


def _param_hint(param_name: str) -> Tuple[str, str]:
    """Category + suffix hint from a MOVE/FB port name (:MV, :22, :1 …)."""
    if not param_name:
        return "", ""
    if param_name in _PARAM_HINT:
        return _PARAM_HINT[param_name]
    if param_name.isdigit():
        n = int(param_name)
        # ABB MOVE / logic ports: low = DI inputs, mid = DO, high = AO
        if n >= 20:
            return "AO", "OUT"
        if n >= 10:
            return "DO", "CMD"
        return "DI", "IN"
    return "", ""


def _block_param_int(block: _Block, *names: str) -> Optional[int]:
    """First integer body among named :PARAM lines (e.g. IOADDR, CHANNEL)."""
    want = {n.upper() for n in names}
    for param in block.params:
        if param.name.upper() not in want:
            continue
        m = re.search(r"\d+", param.body or "")
        if m:
            return int(m.group(0))
    return None


def _plants_from_body(body: str) -> List[str]:
    """Plant device tags found in a parameter body (dotted or colon-form)."""
    tags: List[str] = []
    seen: Set[str] = set()
    for m in _SOFT_DOTTED.finditer(body or ""):
        tag = _clean_tag(m.group("tag"))
        if tag and tag.upper() not in seen and _is_valid_tag(tag):
            seen.add(tag.upper())
            tags.append(tag)
    for m in _SOFT_COLON.finditer(body or ""):
        base = _clean_tag(m.group("base"))
        suf = (m.group("suf") or "").upper()
        if not base or _SKIP_COLON_ATTR.match(suf):
            continue
        tag = f"{base}.{suf}"
        if tag.upper() not in seen and _is_valid_tag(tag):
            seen.add(tag.upper())
            tags.append(tag)
    return tags


def _hw_from_body(body: str) -> List[Tuple[str, str, str, str]]:
    """Hardwired (family, category, card, channel) tuples in a parameter body."""
    found: List[Tuple[str, str, str, str]] = []
    for m in _IO_HW.finditer(body or ""):
        family, category = _normalise_prefix(m.group("prefix").upper())
        card = m.group("card")
        channel = m.group("channel") or "0"
        found.append((family, category, card, channel))
    return found


def _hw_addr(family: str, card: str, channel: str) -> str:
    return f"{family}{card}.{channel}" if channel and channel != "0" else f"{family}{card}"


def _resolve_hw_device_tag(
    *,
    block: Optional[_Block],
    param_name: str,
    param_suffix: str,
    line: str,
    addr: str,
) -> str:
    """Derive a device tag for a hardwired address using block context."""
    base = ""
    if block is not None:
        base = block.dbinst or block.title_tag

    if not base:
        n_m = _N_SIGNAL.search(line)
        if n_m:
            name = n_m.group("name").upper()
            candidate = re.split(r"[_\-]", name, maxsplit=1)[0]
            if re.search(r"[A-Z]", candidate) and len(candidate) >= 3:
                base = candidate

    if base:
        base = base.split(":")[0]
        if "." in base:
            return base
        return f"{base}.{param_suffix}" if param_suffix else base

    return addr.upper()


def _stage_hardwired_and_soft_per_block(
    block: _Block, out: _CandidateSet
) -> None:
    """Stages 4A/4B/4C/4D on a single block."""
    for param in block.params:
        line = param.raw
        body = param.body
        param_name = param.name.upper() if param.name != "_WIRE_" else ""
        param_cat, param_suffix = _param_hint(param_name)

        # 4A — hardwired
        for m in _IO_HW.finditer(body):
            raw_prefix = m.group("prefix").upper()
            family, category = _normalise_prefix(raw_prefix)
            card = m.group("card")
            channel = m.group("channel")
            addr = f"{family}{card}.{channel}" if channel else f"{family}{card}"

            # Prefer category-native suffix when MOVE ports are generic numbers
            cat_suffix = {
                "AI": "MV", "AI800_": "MV",
                "AO": "OUT", "AO800_": "OUT",
                "DI": "IN", "DI800_": "IN",
                "DO": "CMD", "DO800_": "CMD",
            }.get(family, param_suffix)
            use_suffix = (
                param_suffix
                if (param_name and not param_name.isdigit())
                else (cat_suffix or param_suffix)
            )
            device_tag = _resolve_hw_device_tag(
                block=block,
                param_name=param_name,
                param_suffix=use_suffix,
                line=line,
                addr=addr,
            )
            named_io = param_name in _STRONG_IO_PARAMS
            out.add(
                _Candidate(
                    addr=addr,
                    device_tag=device_tag,
                    category=category,
                    priority=5 if named_io else 3,
                    hardwired=True,
                    source=f"HW/{block.obj_id}:{param_name}",
                ),
                skip_reason="",
            )

        # 4B — soft dotted device tags
        for m in _SOFT_DOTTED.finditer(body):
            tag = _clean_tag(m.group("tag"))
            if not tag or "." not in tag:
                continue
            suffix = tag.rsplit(".", 1)[-1].upper()
            cat = _SUFFIX_CATEGORY.get(suffix) or param_cat or "AI"
            if block.dbinst and tag.upper() == block.dbinst.upper():
                continue
            out.add(
                _Candidate(
                    addr=f"{cat}0.0",
                    device_tag=tag,
                    category=cat,
                    priority=2,
                    hardwired=False,
                    source=f"SOFT/{block.obj_id}:{param_name}",
                )
            )

        # 4C — colon-form soft (=82LIC428:BLK_D → 82LIC428.BLK_D)
        for m in _SOFT_COLON.finditer(body):
            base = _clean_tag(m.group("base"))
            suf = (m.group("suf") or "").upper()
            if not base or _SKIP_COLON_ATTR.match(suf):
                continue
            cat = _SUFFIX_CATEGORY.get(suf) or param_cat or "AI"
            tag = f"{base}.{suf}"
            out.add(
                _Candidate(
                    addr=f"{cat}0.0",
                    device_tag=tag,
                    category=cat,
                    priority=2,
                    hardwired=False,
                    source=f"COLON/{block.obj_id}:{param_name}",
                )
            )

        # 4D — plant tag on I/O param name (bare loop tag or dotted)
        if param_name in _IO_PARAMS:
            for m in _PLANT_ON_IO_PARAM.finditer(body):
                raw_tag = _clean_tag(m.group("tag"))
                if not raw_tag:
                    continue
                if _IO_HW.match("=" + raw_tag):
                    continue                # captured by 4A already
                if "." in raw_tag:
                    suffix = raw_tag.rsplit(".", 1)[-1].upper()
                    cat = _SUFFIX_CATEGORY.get(suffix) or param_cat or "AI"
                    out.add(
                        _Candidate(
                            addr=f"{cat}0.0",
                            device_tag=raw_tag,
                            category=cat,
                            priority=2,
                            hardwired=False,
                            source=f"PARAM/{block.obj_id}:{param_name}",
                        )
                    )
                elif param_suffix:
                    tag = f"{raw_tag}.{param_suffix}"
                    if block.dbinst and raw_tag == block.dbinst.upper():
                        continue
                    out.add(
                        _Candidate(
                            addr=f"{(param_cat or 'AI')}0.0",
                            device_tag=tag,
                            category=param_cat or "AI",
                            priority=2,
                            hardwired=False,
                            source=f"PARAM/{block.obj_id}:{param_name}",
                        )
                    )
                elif block.dbinst and raw_tag == block.dbinst.upper():
                    continue


def _stage_pcu_io(block: _Block, out: _CandidateSet, page_title_tag: str) -> None:
    """Stage 4F — PCU-I / PCU-O pulse-counter I/O.

    Advant PCU modules do not use ``=AIcard.channel`` strings. The slot is
    ``:IOADDR`` (module address, e.g. 192) and the channel is ``:CHANNEL``
    (1..n on that pulse module). Bind those values onto the page loop tag.
    """
    if block.block_type not in ("PCU-I", "PCU-O"):
        return
    ioaddr = _block_param_int(block, "IOADDR")
    channel = _block_param_int(block, "CHANNEL")
    if ioaddr is None:
        return
    ch = str(channel) if channel is not None and channel > 0 else "0"
    base = page_title_tag or block.title_tag or block.dbinst or ""
    base = base.split(":")[0].strip()
    if not base:
        return
    if block.block_type == "PCU-I":
        tag = f"{base}.SPEEDMV"
        family, category = "AI", "AI"
    else:
        tag = f"{base}.PULSEOUT"
        family, category = "DO", "DO"
    if not _is_valid_tag(tag):
        return
    addr = _hw_addr(family, str(ioaddr), ch)
    out.attach_address(
        tag,
        addr,
        category,
        priority=6,
        source=f"PCU/{block.obj_id}:IOADDR{ioaddr}.CH{ch}",
    )


def _stage_bind_block_addresses(block: _Block, out: _CandidateSet) -> None:
    """Stage 4G — join hardware addresses onto plant tags in the same block.

    Relationships used (in order of reliability):
      1. Named FB I/O param (:MV, :MC, :SO1, :CLS, …) + :DBINST / page title
      2. MOVE port pairs (:21 plant ↔ :22 =AOx.y, same for :23/:24, :1/:2)
    Device tags already extracted by 4B/4C are only *addressed*, not renamed.
    """
    identity = block.dbinst or block.title_tag or ""
    identity = identity.split(":")[0].strip()

    hw_by_param: Dict[str, Tuple[str, str, str, str]] = {}
    plant_by_param: Dict[str, str] = {}
    for param in block.params:
        if param.name == "_WIRE_":
            continue
        hws = _hw_from_body(param.body)
        plants = _plants_from_body(param.body)
        if hws:
            hw_by_param[param.name.upper()] = hws[0]
        if plants:
            plant_by_param[param.name.upper()] = plants[0]

        # Named I/O param carrying HW → identity.suffix
        if identity and hws and param.name.upper() in _STRONG_IO_PARAMS:
            _cat, suffix = _PARAM_HINT[param.name.upper()]
            family, category, card, channel = hws[0]
            tag = identity if "." in identity else f"{identity}.{suffix}"
            out.attach_address(
                tag,
                _hw_addr(family, card, channel),
                category,
                priority=6,
                source=f"JOIN/{block.obj_id}:{param.name}",
            )

    pair_ports = (
        ("21", "22"), ("23", "24"), ("25", "26"),
        ("11", "12"), ("13", "14"),
        ("1", "2"), ("3", "4"),
    )
    for left, right in pair_ports:
        _bind_port_pair(out, block, hw_by_param, plant_by_param, left, right)


def _bind_port_pair(
    out: _CandidateSet,
    block: _Block,
    hw_by_param: Dict[str, Tuple[str, str, str, str]],
    plant_by_param: Dict[str, str],
    left: str,
    right: str,
) -> None:
    hw_left = hw_by_param.get(left)
    hw_right = hw_by_param.get(right)
    plant_left = plant_by_param.get(left)
    plant_right = plant_by_param.get(right)
    if hw_left and plant_right and not hw_right:
        family, category, card, channel = hw_left
        out.attach_address(
            plant_right,
            _hw_addr(family, card, channel),
            category,
            priority=6,
            source=f"MOVE/{block.obj_id}:{left}->{right}",
        )
    elif hw_right and plant_left and not hw_left:
        family, category, card, channel = hw_right
        out.attach_address(
            plant_left,
            _hw_addr(family, card, channel),
            category,
            priority=6,
            source=f"MOVE/{block.obj_id}:{left}->{right}",
        )


def _stage_global_fallback(joined_text: str, out: _CandidateSet) -> int:
    """Stage 5 — whole-page rescan; catches HW addresses still not registered."""
    recovered = 0

    for m in _IO_HW.finditer(joined_text):
        raw_prefix = m.group("prefix").upper()
        family, category = _normalise_prefix(raw_prefix)
        card = m.group("card")
        channel = m.group("channel")
        addr = f"{family}{card}.{channel}" if channel else f"{family}{card}"
        key = f"HW:{addr.upper()}"
        if key in out._by_key:
            continue
        if out.add(
            _Candidate(
                addr=addr,
                device_tag=addr.upper(),
                category=category,
                priority=2,
                hardwired=True,
                source="FALLBACK-HW",
            )
        ):
            recovered += 1

    for m in _SOFT_DOTTED.finditer(joined_text):
        tag = _clean_tag(m.group("tag"))
        if not tag or "." not in tag:
            continue
        suffix = tag.rsplit(".", 1)[-1].upper()
        cat = _SUFFIX_CATEGORY.get(suffix) or "AI"
        if not _is_valid_tag(tag):
            continue
        soft_key = f"SOFT:{tag.upper()}"
        if soft_key in out._by_key:
            continue
        # If already owned by a HW entry, skip
        if any(v.device_tag.upper() == tag.upper() for v in out._by_key.values()):
            continue
        if out.add(
            _Candidate(
                addr=f"{cat}0.0",
                device_tag=tag,
                category=cat,
                priority=1,
                hardwired=False,
                source="FALLBACK-SOFT",
            )
        ):
            recovered += 1

    for m in _SOFT_COLON.finditer(joined_text):
        base = _clean_tag(m.group("base"))
        suf = (m.group("suf") or "").upper()
        if not base or _SKIP_COLON_ATTR.match(suf):
            continue
        cat = _SUFFIX_CATEGORY.get(suf) or "AI"
        tag = f"{base}.{suf}"
        soft_key = f"SOFT:{tag.upper()}"
        if soft_key in out._by_key:
            continue
        if any(v.device_tag.upper() == tag.upper() for v in out._by_key.values()):
            continue
        if out.add(
            _Candidate(
                addr=f"{cat}0.0",
                device_tag=tag,
                category=cat,
                priority=1,
                hardwired=False,
                source="FALLBACK-COLON",
            )
        ):
            recovered += 1

    return recovered


# ──────────────────────────────────────────────────────────────────────────
# Public reader
# ──────────────────────────────────────────────────────────────────────────

class AaxReader:
    """Multi-stage AAX PC export reader → ``List[PageContent]``.

    Attributes exposed for observability:
        ``warnings``      — human-readable warnings collected across the file.
        ``stats``         — per-stage counters (populated after ``read_all_pages``).
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.warnings: List[str] = []
        self.stats: Dict[str, int] = {}
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"AAX file not found at path: {file_path}")

    # ---- public entry point ------------------------------------------

    def read_all_pages(self) -> List[PageContent]:
        text = _load_text(Path(self.file_path))
        text = _COMMENT_BLOCK.sub("", text)               # strip (* … *)
        header_meta = _extract_header_metadata(text)
        pages = self._split_and_build_pages(text, header_meta)
        logger.info(
            f"AaxReader loaded {len(pages)} page(s) from {Path(self.file_path).name}"
            + (f" ({len(self.warnings)} warning(s))" if self.warnings else "")
        )
        for w in self.warnings[:20]:
            logger.warning(f"AaxReader: {w}")
        return pages

    # ---- Stage 2 -----------------------------------------------------

    def _split_and_build_pages(
        self, text: str, header_meta: Dict[str, str]
    ) -> List[PageContent]:
        matches = list(_PAGE_SPLIT.finditer(text))
        if not matches:
            body = text.strip()
            return (
                [self._build_page(1, body, header_meta, is_first=True)]
                if body else []
            )

        pages: List[PageContent] = []

        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            page_num = int(match.group(1)) if match.group(1) else idx + 1
            # Do not splice the AAX HEADER preamble into page 1. Metadata is
            # already captured by _extract_header_metadata and re-emitted as
            # mapper hints. Prepending HEADER buried the quoted page title
            # and left Excel Description blank.
            if not body:
                continue
            pages.append(
                self._build_page(page_num, body, header_meta, is_first=(idx == 0))
            )
        return pages

    # ---- Stages 3-7 --------------------------------------------------

    def _build_page(
        self,
        page_number: int,
        body: str,
        header_meta: Dict[str, str],
        *,
        is_first: bool,
    ) -> PageContent:
        raw_lines = [ln.rstrip("\r\n") for ln in body.splitlines()]

        # Cheap noise strip: keep everything except HEADER/BEGIN/END lines
        eng_lines: List[str] = []
        for ln in raw_lines:
            s = ln.strip()
            if not s:
                continue
            if s.upper().startswith(("HEADER", "BEGIN ", "END ")):
                continue
            eng_lines.append(ln)

        title_tag, title_desc = self._page_title(eng_lines)
        blocks, orphans = _segment_blocks(page_number, title_tag, eng_lines)

        cand_set = _CandidateSet()
        for block in blocks:
            _stage_hardwired_and_soft_per_block(block, cand_set)
            _stage_pcu_io(block, cand_set, page_title_tag=title_tag)
            _stage_bind_block_addresses(block, cand_set)

        # Orphan params (rare in real AAX) — treat them as a synthetic block
        if orphans:
            pseudo_block = _Block(
                obj_id="ORPHAN",
                block_type="",
                page_number=page_number,
                title_tag=title_tag,
                params=orphans,
            )
            _stage_hardwired_and_soft_per_block(pseudo_block, cand_set)

        joined_body = "\n".join(eng_lines)
        recovered = _stage_global_fallback(joined_body, cand_set)
        if recovered:
            self.warnings.append(
                f"page {page_number}: fallback recovered {recovered} I/O candidate(s) "
                f"(title '{title_tag or '—'}')"
            )

        # Validation warnings — hardwired refs present in text but not emitted
        text_hw = set()
        for m in _IO_HW.finditer(joined_body):
            raw_prefix = m.group("prefix").upper()
            family, _ = _normalise_prefix(raw_prefix)
            card = m.group("card")
            channel = m.group("channel")
            addr = f"{family}{card}.{channel}" if channel else f"{family}{card}"
            text_hw.add(addr.upper())
        missed = sorted(text_hw - cand_set.hw_addresses())
        if missed:
            self.warnings.append(
                f"page {page_number}: possible skipped hardwired ref(s): "
                + ", ".join(missed[:8]) + ("…" if len(missed) > 8 else "")
            )

        # Stage 7 — emit. Description hints go first so DescriptionMapper
        # binds the page title before raw :param lines can steal the match.
        synth = cand_set.emit_lines()
        page_desc = _sanitize_desc_for_mapper(title_desc)
        desc_hints: List[str] = []
        if title_tag and page_desc:
            desc_hints.append(f"{title_tag} {page_desc}")
            desc_hints.append(f"{title_tag}: {page_desc}")
        if page_desc:
            seen_loops = set()
            for cand in synth:
                if "/" not in cand:
                    continue
                device = cand.split("/", 1)[1].strip()
                loop = device.rsplit(".", 1)[0] if "." in device else device
                if not loop or loop in seen_loops:
                    continue
                seen_loops.add(loop)
                desc_hints.append(f"{loop} {page_desc}")
                desc_hints.append(f"{loop}: {page_desc}")
        out_lines: List[str] = list(desc_hints)
        if is_first and header_meta:
            out_lines.extend(_metadata_hint_lines(header_meta))
        out_lines.extend(eng_lines)
        out_lines.extend(synth)

        page_text = "\n".join(out_lines)

        # Track corpus-level stats
        self.stats.setdefault("blocks", 0)
        self.stats.setdefault("candidates", 0)
        self.stats["blocks"] += len(blocks)
        self.stats["candidates"] += len(synth)

        return PageContent(
            page_number=page_number,
            text=page_text,
            words=[],
            raw_lines=out_lines,
            text_layers={
                "aax": joined_body,
                "aax_synth": "\n".join(synth),
            },
            low_text_density=False,
        )

    # ---- helpers ------------------------------------------------------

    @staticmethod
    def _page_title(lines: List[str]) -> Tuple[str, str]:
        """Return the quoted PCD-PAGE title, skipping AAX HEADER / object lines."""
        for ln in lines:
            s = ln.strip()
            if not s.startswith('"'):
                continue
            m = _PAGE_TITLE.match(s)
            if not m:
                continue
            return (m.group("tag") or "").upper(), (m.group("desc") or "").strip()
        return "", ""


def _sanitize_desc_for_mapper(text: str) -> str:
    """Strip characters DescriptionMapper treats as drawing noise.

    Keeps letters/digits/spaces so `{loop} {desc}` lines bind in Excel.
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = s.replace("<=>", " to ")
    s = s.replace("\\", " ")
    s = s.replace("/", " ")
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r":\d+", " ", s)
    s = s.replace(":", " ")
    s = re.sub(r"[^A-Za-z0-9\s/#.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 78:
        s = s[:78].rsplit(" ", 1)[0].strip()
    # DescriptionMapper rejects any text containing substring "ACT", which
    # blanks titles like "PIDCON Derivative & Integral Action Setup".
    s = re.sub(r"\bACTION\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _metadata_hint_lines(meta: Dict[str, str]) -> List[str]:
    hints: List[str] = []
    for key in (
        "IEC_Project1",
        "IEC_Project2",
        "IEC_Project3",
        "IEC_Title2",
        "R_Text1",
        "R_Text3",
    ):
        bit = meta.get(key, "")
        if not bit:
            continue
        hints.append(bit)
        if re.search(r"\bPM\d+", bit, re.IGNORECASE):
            hints.append(bit.replace("\\", "/"))
    if meta.get("IEC_DocNo"):
        hints.append(f"Document No {meta['IEC_DocNo']}")
    return hints
