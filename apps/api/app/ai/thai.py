"""Thai text normalisation for matching (AGENTS.md: normalise before substring/regex matching)."""

import re
import unicodedata

_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
_WHITESPACE = re.compile(r"\s+")
_TONES = re.compile("([่-๋])[่-๋]+")  # stacked tone marks: keep the last
_REPEATED_MARK = re.compile("([ัิ-ฺ็์-๎])\\1+")  # same mark repeated


def normalize_th(text: str) -> str:
    """NFC, no zero-width chars, one space between words, no stacked or repeated marks."""
    text = unicodedata.normalize("NFC", _ZERO_WIDTH.sub("", text))
    text = _TONES.sub(lambda m: m.group(0)[-1], text)
    text = _REPEATED_MARK.sub(r"\1", text)
    return _WHITESPACE.sub(" ", text).strip()
