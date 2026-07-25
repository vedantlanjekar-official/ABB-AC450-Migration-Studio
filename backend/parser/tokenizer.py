import re
from typing import List, Tuple, Any
from backend.parser.token import Token, TokenType
from backend.core.logging import get_logger

class Tokenizer:
    """
    Stage 4 — Lexical Tokenizer Module.
    Converts continuous engineering lines into a stream of strongly-typed Token objects.
    """

    DEFAULT_START_REGEX = re.compile(
        r'^\s*DEFAULT[S]?[:\s\-]+([A-Z0-9_]+)\b',
        re.IGNORECASE
    )

    DEFAULT_END_REGEX = re.compile(
        r'^\s*\*{0,10}\s*END\s+OF\s+DEFAULTS?\s*\*{0,10}\s*$',
        re.IGNORECASE
    )

    OBJECT_START_REGEX = re.compile(
        r'^\s*([A-Z]{2,12})\s*(\d+(?:\.\d+)*)\b'
    )

    PARAM_COLON_REGEX = re.compile(
        r'^\s*:([A-Z0-9_]{1,30})\s*(.*)$',
        re.IGNORECASE
    )

    def __init__(self, job_id: str = None):
        self.logger = get_logger(job_id)

    def tokenize(self, cleaned_lines: List[Tuple[int, str]]) -> List[Token]:
        """
        Tokenizes continuous engineering lines into a Token stream.
        """
        tokens: List[Token] = []

        for page_num, line in cleaned_lines:
            line_str = line.strip()
            if not line_str:
                continue

            # 1. Check DEFAULT_END (*** END OF DEFAULTS ***)
            if self.DEFAULT_END_REGEX.match(line_str) or "END OF DEFAULT" in line_str.upper():
                tokens.append(
                    Token(
                        token_type=TokenType.DEFAULT_END,
                        raw_line=line,
                        page_number=page_num
                    )
                )
                continue

            # 2. Check DEFAULT_START (DEFAULT AIS, DEFAULT AI, DEFAULT AOS)
            match_def = self.DEFAULT_START_REGEX.match(line_str)
            if match_def:
                raw_name = match_def.group(1).upper()
                tokens.append(
                    Token(
                        token_type=TokenType.DEFAULT_START,
                        raw_line=line,
                        page_number=page_num,
                        name=raw_name
                    )
                )
                continue

            # Fallback DEFAULT start check
            if line_str.upper().startswith("DEFAULT"):
                parts = line_str.split()
                if len(parts) >= 2:
                    raw_name = parts[1].strip(":-_").upper()
                    if raw_name and raw_name not in ("OF", "DEFAULTS", "BLOCK", "SECTION"):
                        tokens.append(
                            Token(
                                token_type=TokenType.DEFAULT_START,
                                raw_line=line,
                                page_number=page_num,
                                name=raw_name
                            )
                        )
                        continue

            # 3. Check OBJECT_START (AI1.4, AI1.1, AO2.1, PIDCON1, MOTCON1)
            match_obj = self.OBJECT_START_REGEX.match(line_str)
            if match_obj:
                family = match_obj.group(1).upper()
                index = match_obj.group(2)
                identifier = f"{family}{index}"
                tokens.append(
                    Token(
                        token_type=TokenType.OBJECT_START,
                        raw_line=line,
                        page_number=page_num,
                        family=family,
                        identifier=identifier,
                        index=index
                    )
                )
                continue

            # 4. Check PARAMETER (:NAME 940PI726.MV, :UNIT bar, :DESCR)
            match_param = self.PARAM_COLON_REGEX.match(line_str)
            if match_param:
                param_key = match_param.group(1).upper()
                raw_val = match_param.group(2).strip()
                cleaned_val = self._clean_value(raw_val)
                tokens.append(
                    Token(
                        token_type=TokenType.PARAMETER,
                        raw_line=line,
                        page_number=page_num,
                        name=param_key,
                        value=cleaned_val
                    )
                )
                continue

            # 5. Fallback TEXT
            tokens.append(
                Token(
                    token_type=TokenType.TEXT,
                    raw_line=line,
                    page_number=page_num
                )
            )

        self.logger.info(f"Tokenizer produced {len(tokens)} Token(s) from {len(cleaned_lines)} cleaned lines.")
        return tokens

    def _clean_value(self, val_str: str) -> Any:
        if not val_str:
            return ""

        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            return val_str[1:-1].strip()

        if val_str.upper() in ('TRUE', 'YES', 'ON'):
            return True
        if val_str.upper() in ('FALSE', 'NO', 'OFF'):
            return False

        try:
            if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
                return int(val_str)
        except ValueError:
            pass

        try:
            return float(val_str)
        except ValueError:
            pass

        return val_str.strip('"\'')
