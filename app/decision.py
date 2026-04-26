from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models import BasketItemRequest, MatchResult, ProductCandidate
from app.scorer import score_candidate


EXACT_MATCH_THRESHOLD = 0.62
SUBSTITUTE_THRESHOLD = 0.45

MatchStatus = Literal["exact_match", "substitute", "unmatched"]


@dataclass(frozen=True)
class DecisionResult:
    """Represents the match decision for one basket item request."""

    status: MatchStatus
    best_match: MatchResult | None
    best_score: float
    match_notes: str


def classify_score(score: float) -> MatchStatus:
    """Classify score into exact/substitute/unmatched buckets."""
    if score >= EXACT_MATCH_THRESHOLD:
        return "exact_match"
    if score >= SUBSTITUTE_THRESHOLD:
        return "substitute"
    return "unmatched"


def choose_best_candidate(
    request: BasketItemRequest, candidates: list[ProductCandidate]
) -> DecisionResult:
    """Pick the highest scoring candidate and return decision + explanation."""
    if not candidates:
        return DecisionResult(
            status="unmatched",
            best_match=None,
            best_score=0.0,
            match_notes="No candidates returned for this request.",
        )

    scored = [(candidate, score_candidate(request, candidate)) for candidate in candidates]
    best_candidate, breakdown = max(
        scored,
        key=lambda item: (
            item[1].total_score,
            item[1].size_match,
            item[1].token_similarity,
            item[0].retailer_product_id,
        ),
    )

    status = classify_score(breakdown.total_score)
    if status == "unmatched":
        return DecisionResult(
            status=status,
            best_match=None,
            best_score=breakdown.total_score,
            match_notes=f"Unmatched: {breakdown.match_notes}",
        )

    result = MatchResult(
        request_line_id=request.line_id,
        candidate=best_candidate,
        confidence=breakdown.total_score,
        rationale=breakdown.match_notes,
        selected=True,
    )
    return DecisionResult(
        status=status,
        best_match=result,
        best_score=breakdown.total_score,
        match_notes=breakdown.match_notes,
    )
