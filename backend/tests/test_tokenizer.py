import pytest
from backend.parser.token import TokenType
from backend.parser.tokenizer import Tokenizer
from backend.parser.text_cleaner import TextCleaner
from backend.parser.pdf_loader import PageObject

def test_text_cleaner_removes_abb_headers():
    cleaner = TextCleaner("test_cleaner")
    pages = [
        PageObject(
            page_number=1,
            raw_text="""
ABB Automation                         DATABASE LISTING                        Sheet 108
Prepared: J. Doe                       Approved: M. Smith                      Cont. 109
Document Number: 3BSE008543R101        Revision: B                             Date: 2026-07-21
Copyright (c) ABB Automation Inc. All rights reserved.

DEFAULT AI
  :TYPE ANALOG_INPUT
  :SCANT 1s

AI1.1
  :NAME "PRESSURE_TR"
"""
        )
    ]

    cleaned_lines, ignored_cnt = cleaner.clean_and_merge_pages(pages)
    assert ignored_cnt >= 3, "Expected ABB header noise lines to be stripped"

    text_lines = [t[1] for t in cleaned_lines]
    assert "DEFAULT AI" in text_lines
    assert "AI1.1" in text_lines

def test_tokenizer_produces_typed_tokens():
    tokenizer = Tokenizer("test_tokenizer")
    lines = [
        (1, "DEFAULT AIS"),
        (1, ":UNIT %"),
        (1, ":RANGEMAX 100.000"),
        (1, ":DESCR"),
        (1, "*** END OF DEFAULTS ***"),
        (1, "AI1.4"),
        (1, ":NAME 940PI726.MV"),
        (1, ":UNIT bar"),
    ]

    tokens = tokenizer.tokenize(lines)
    types = [t.token_type for t in tokens]

    assert types[0] == TokenType.DEFAULT_START
    assert tokens[0].name == "AIS"

    assert types[1] == TokenType.PARAMETER
    assert tokens[1].name == "UNIT"
    assert tokens[1].value == "%"

    # Preserves empty parameter (:DESCR -> DESCR: "")
    assert types[3] == TokenType.PARAMETER
    assert tokens[3].name == "DESCR"
    assert tokens[3].value == ""

    assert types[4] == TokenType.DEFAULT_END

    assert types[5] == TokenType.OBJECT_START
    assert tokens[5].family == "AI"
    assert tokens[5].identifier == "AI1.4"
    assert tokens[5].index == "1.4"

    assert types[6] == TokenType.PARAMETER
    assert tokens[6].name == "NAME"
    assert tokens[6].value == "940PI726.MV"
