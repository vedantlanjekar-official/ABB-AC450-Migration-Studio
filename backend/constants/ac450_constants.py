import re

# Regex for detecting ABB AC450 DB Element Headers
# Example tags: AI1.4, AO2.6, PIDCON3, MOTCON10, VALVECON2, DS5, DAT1, DIC1, DOC1, AIC1, AOC1, TEXT1, MANSTN1, RATIOSTN1, TTDVAR1
# Generic matching pattern:
# Group 1: Element type string (uppercase letters, e.g. AI, AO, PIDCON, MOTCON, VALVECON, DS, DAT, TEXT)
# Group 2: Index number (e.g. 1.4, 2.6, 3, 100.1)
ELEMENT_HEADER_PATTERN = re.compile(
    r'^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\s*$',
    re.MULTILINE
)

# Alternative inline header pattern (e.g., when tag appears on a line with parameters or trailing text)
ELEMENT_INLINE_HEADER_PATTERN = re.compile(
    r'^\s*([A-Z]{2,12})(\d+(?:\.\d+)*)\b',
    re.MULTILINE
)

# Regex for detecting colon parameters inside an element block
# Examples: :NAME "AI_PUMP_01", :UNIT "BAR", :RANGEMAX 100.0, :DESCR "Pressure Transporter"
# Group 1: Key (without colon), e.g. NAME, UNIT, RANGEMAX
# Group 2: Raw Value string
PARAM_COLON_PATTERN = re.compile(
    r':([A-Z0-9_]{1,30})\s*(.*?)(?=\s+:[A-Z0-9_]{1,30}|\s*$)',
    re.DOTALL
)

# Common AC450 Element Types (for display ordering / tab prioritization)
KNOWN_ELEMENT_TYPES = [
    "AI", "AIC", "AO", "AOC", "DI", "DIC", "DO", "DOC",
    "DAT", "DS", "PIDCON", "MOTCON", "VALVECON", "MANSTN",
    "RATIOSTN", "TEXT", "TTDVAR"
]
