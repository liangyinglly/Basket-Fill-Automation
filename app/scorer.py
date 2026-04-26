from __future__ import annotations

from dataclasses import dataclass
import re

from app.models import BasketItemRequest, ProductCandidate
from app.normalize import normalize_query_string


TOKEN_WEIGHT = 0.45
BRAND_WEIGHT = 0.20
SIZE_WEIGHT = 0.20
NOTES_WEIGHT = 0.10
CATEGORY_WEIGHT = 0.05

_STOP_TOKENS = {
    "a",
    "an",
    "and",
    "for",
    "fresh",
    "of",
    "or",
    "pack",
    "the",
    "with",
}
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(gallon|gal|dozen|count|ct|lb|pound|oz|ounce)s?")
_UNIT_ALIASES = {
    "gallon": "gal",
    "gal": "gal",
    "dozen": "ct",
    "count": "ct",
    "ct": "ct",
    "lb": "lb",
    "pound": "lb",
    "oz": "oz",
    "ounce": "oz",
}
_CATEGORY_KEYWORDS = {
    "dairy": {"milk", "yogurt", "cheese", "butter"},
    "eggs": {"egg", "eggs"},
    "meat": {"chicken", "breast", "beef", "pork", "turkey"},
}


@dataclass(frozen=True)
class ScoreBreakdown:
    """Component scores and explanation for one request/candidate comparison."""

    total_score: float
    token_similarity: float
    brand_match: float
    size_match: float
    notes_keyword_match: float
    category_bias: float
    match_notes: str


def _tokens(text: str) -> set[str]:
    normalized = normalize_query_string(text)
    return {
        token
        for token in normalized.split()
        if len(token) > 1 and token not in _STOP_TOKENS
    }


def _extract_size_from_request(request: BasketItemRequest) -> tuple[float, str] | None:
    unit = _UNIT_ALIASES.get(normalize_query_string(request.unit))
    if unit is None:
        return None
    quantity = float(request.quantity)
    if unit == "ct" and quantity == 1:
        # Handle common "1 dozen" request representation.
        if normalize_query_string(request.unit) == "dozen":
            quantity = 12.0
    return (quantity, unit)


def _extract_size_from_candidate(candidate: ProductCandidate) -> tuple[float, str] | None:
    merged_text = " ".join(
        part for part in [candidate.title, candidate.size_text or ""] if part
    )
    normalized = normalize_query_string(merged_text)
    match = _SIZE_RE.search(normalized)
    if match is None:
        return None
    quantity = float(match.group(1))
    raw_unit = match.group(2)
    unit = _UNIT_ALIASES.get(raw_unit)
    if unit is None:
        return None
    if raw_unit == "dozen":
        quantity *= 12
    return (quantity, unit)


def _infer_category(tokens: set[str], explicit_category: str | None = None) -> str | None:
    if explicit_category:
        return normalize_query_string(explicit_category)
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if tokens & keywords:
            return category
    return None


def _brand_score(request: BasketItemRequest, candidate: ProductCandidate) -> float:
    preferred = (request.preferred_brand or "").strip()
    if not preferred:
        return 0.5
    preferred_norm = normalize_query_string(preferred)
    candidate_brand_tokens = _tokens(
        " ".join(filter(None, [candidate.brand or "", candidate.title]))
    )
    return 1.0 if preferred_norm in candidate_brand_tokens else 0.0


def _size_score(request: BasketItemRequest, candidate: ProductCandidate) -> float:
    request_size = _extract_size_from_request(request)
    candidate_size = _extract_size_from_candidate(candidate)
    if request_size is None or candidate_size is None:
        return 0.3

    req_qty, req_unit = request_size
    cand_qty, cand_unit = candidate_size
    if req_unit != cand_unit:
        return 0.0
    if req_qty == cand_qty:
        return 1.0

    ratio = min(req_qty, cand_qty) / max(req_qty, cand_qty)
    if ratio >= 0.8:
        return 0.6
    return 0.2


def _notes_keyword_score(request: BasketItemRequest, candidate: ProductCandidate) -> float:
    notes = (request.notes or "").strip()
    if not notes:
        return 0.5
    note_tokens = _tokens(notes)
    if not note_tokens:
        return 0.5
    candidate_tokens = _tokens(" ".join(filter(None, [candidate.title, candidate.brand or ""])))
    overlap = note_tokens & candidate_tokens
    return len(overlap) / len(note_tokens)


def _token_similarity_score(request: BasketItemRequest, candidate: ProductCandidate) -> float:
    req_tokens = _tokens(request.name)
    cand_tokens = _tokens(" ".join(filter(None, [candidate.title, candidate.brand or ""])))
    if not req_tokens or not cand_tokens:
        return 0.0
    intersection = req_tokens & cand_tokens
    union = req_tokens | cand_tokens
    return len(intersection) / len(union)


def _category_score(request: BasketItemRequest, candidate: ProductCandidate) -> float:
    req_category = _infer_category(_tokens(request.name))
    cand_category = _infer_category(
        _tokens(candidate.title),
        explicit_category=candidate.category,
    )
    if req_category is None or cand_category is None:
        return 0.5
    return 1.0 if req_category == cand_category else 0.2


def score_candidate(
    request: BasketItemRequest, candidate: ProductCandidate
) -> ScoreBreakdown:
    """Compute deterministic match score and detailed notes for one candidate."""
    token_similarity = _token_similarity_score(request, candidate)
    brand_match = _brand_score(request, candidate)
    size_match = _size_score(request, candidate)
    notes_keyword_match = _notes_keyword_score(request, candidate)
    category_bias = _category_score(request, candidate)

    total_score = (
        token_similarity * TOKEN_WEIGHT
        + brand_match * BRAND_WEIGHT
        + size_match * SIZE_WEIGHT
        + notes_keyword_match * NOTES_WEIGHT
        + category_bias * CATEGORY_WEIGHT
    )

    match_notes = (
        f"token={token_similarity:.2f}, "
        f"brand={brand_match:.2f}, "
        f"size={size_match:.2f}, "
        f"notes={notes_keyword_match:.2f}, "
        f"category={category_bias:.2f}, "
        f"total={total_score:.2f}"
    )

    return ScoreBreakdown(
        total_score=total_score,
        token_similarity=token_similarity,
        brand_match=brand_match,
        size_match=size_match,
        notes_keyword_match=notes_keyword_match,
        category_bias=category_bias,
        match_notes=match_notes,
    )

