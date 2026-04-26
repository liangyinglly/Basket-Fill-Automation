from __future__ import annotations

import re


_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_query_string(value: str) -> str:
    """Normalize free-text into a stable lowercase search query string."""
    lowered = value.strip().lower()
    without_punct = _NON_ALNUM_RE.sub(" ", lowered)
    return _SPACE_RE.sub(" ", without_punct).strip()

