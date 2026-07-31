import re

# Regex for detecting ABB AC450 DB Element Headers
# Supported tags: AI1.4, AO2.6, DI3.1, DO4.2,
#                 AI8001.1 / AI800_1.1, AO8002.1 / AO800_2.1, etc.
# Prefer underscore and concatenated 800-series before letter-only AI/AO/DI/DO
ELEMENT_HEADER_PATTERN = re.compile(
    r'^\s*(AI800|AO800|DI800|DO800|[A-Z]{2,12})(?:_|\s*)?(\d+(?:\.\d+)*)\s*$',
    re.MULTILINE | re.IGNORECASE
)

# Alternative inline header pattern (e.g., when tag appears on a line with parameters or trailing text)
ELEMENT_INLINE_HEADER_PATTERN = re.compile(
    r'^\s*(AI800|AO800|DI800|DO800|[A-Z]{2,12})(?:_)?(\d+(?:\.\d+)*)\b',
    re.MULTILINE | re.IGNORECASE
)

# Regex for detecting colon parameters inside an element block
# Examples: :NAME "AI_PUMP_01", :UNIT "BAR", :RANGEMAX 100.0, :DESCR "Pressure Transporter"
# Group 1: Key (without colon), e.g. NAME, UNIT, RANGEMAX
# Group 2: Raw Value string
PARAM_COLON_PATTERN = re.compile(
    r':([A-Z0-9_]{1,30})\s*(.*?)(?=\s+:[A-Z0-9_]{1,30}|\s*$)',
    re.DOTALL
)

# Only these eight I/O engineering tag families are extracted, validated, and exported.
# Explicitly ignored (examples): AIC, AOC, DAT, DIC, DOC, DS, MANSTN, MMCX,
# PIDCON/PIDCONJS, SEQ, TTDLOG, TEXT, RATIOSTN, MOTCON, VALVECON, and any other type.
SUPPORTED_DB_ELEMENT_TYPES = frozenset({
    "AI", "AO", "DI", "DO",
    "AI800", "AO800", "DI800", "DO800",
})

# Display ordering / tab prioritization (must match the extraction whitelist)
KNOWN_ELEMENT_TYPES = [
    "AI", "AO", "DI", "DO",
    "AI800", "AO800", "DI800", "DO800",
]
