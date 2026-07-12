"""Text normalization helpers.

These are deliberately small, pure functions so they're trivial to unit
test and reuse from both the matching service and admin data-import
tooling.
"""
from __future__ import annotations

import re
import unicodedata

# Matches a stray trailing rank number in the supplied dataset, e.g.
# "Luffy 2" -> "Luffy". Only strips a *trailing* integer preceded by
# whitespace, so legitimate answers containing numbers (e.g. "Cowboy Bebop")
# are left untouched.
_TRAILING_RANK_NUMBER = re.compile(r"\s+\d+\s*$")

# Anything that isn't a letter, digit, or whitespace, after Unicode
# normalization. Keeps non-Latin scripts (e.g. Japanese, Persian) intact.
_SYMBOLS = re.compile(r"[^\w\s]", flags=re.UNICODE)

_MULTI_SPACE = re.compile(r"\s+")


def strip_trailing_rank_number(text: str) -> str:
    """Remove a stray trailing rank number, e.g. 'Luffy 2' -> 'Luffy'.

    The supplied database stores each answer's board rank appended to the
    text itself (a data quirk), separate from the actual ``points``
    column. This undoes that so matching operates on the real name.
    """
    return _TRAILING_RANK_NUMBER.sub("", text).strip()


def normalize(text: str) -> str:
    """Normalize text for comparison: casefold, strip symbols/rank suffix,
    collapse whitespace, and normalize Unicode form.

    This is the canonical normalization used everywhere answers are
    compared: exact match, alias lookup, and as the pre-step to fuzzy
    matching.
    """
    if not text:
        return ""
    text = strip_trailing_rank_number(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    text = _SYMBOLS.sub("", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text
