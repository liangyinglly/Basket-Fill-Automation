from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.ai_reranker import AIReranker, ScoredCandidate, should_invoke_ai_reranker
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
    request: BasketItemRequest,
    candidates: list[ProductCandidate],
    *,
    enable_ai_reranker: bool = False,
    ai_reranker: AIReranker | None = None,
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
    scored_by_id = {candidate.retailer_product_id: breakdown for candidate, breakdown in scored}
    best_candidate, breakdown = max(
        scored,
        key=lambda item: (
            item[1].total_score,
            item[1].size_match,
            item[1].token_similarity,
            item[0].retailer_product_id,
        ),
    )
    ai_note = "ai_invoked=false reason=disabled"

    if enable_ai_reranker:
        scored_candidates = [
            ScoredCandidate(
                candidate=candidate,
                score=details.total_score,
                match_notes=details.match_notes,
            )
            for candidate, details in scored
        ]
        should_invoke, invoke_reason = should_invoke_ai_reranker(scored_candidates)
        if not should_invoke:
            ai_note = f"ai_invoked=false reason={invoke_reason}"
        elif ai_reranker is None:
            ai_note = "ai_invoked=false reason=no_reranker_configured"
        else:
            try:
                outcome = ai_reranker.rerank(
                    request=request,
                    scored_candidates=scored_candidates,
                )
                ai_note = f"ai_invoked=true reason={invoke_reason} detail={outcome.reason}"
                selected_id = outcome.selected_product_id
                if selected_id and selected_id in scored_by_id:
                    selected_candidate = next(
                        candidate
                        for candidate, _ in scored
                        if candidate.retailer_product_id == selected_id
                    )
                    best_candidate = selected_candidate
                    breakdown = scored_by_id[selected_id]
                elif selected_id:
                    ai_note += " fallback=unknown_selected_id"
                else:
                    ai_note += " fallback=no_selection"
            except Exception as exc:  # pragma: no cover - defensive fallback path
                ai_note = f"ai_invoked=false reason=ai_error_fallback detail={type(exc).__name__}"

    status = classify_score(breakdown.total_score)
    if status == "unmatched":
        return DecisionResult(
            status=status,
            best_match=None,
            best_score=breakdown.total_score,
            match_notes=f"Unmatched: {breakdown.match_notes}; {ai_note}",
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
        match_notes=f"{breakdown.match_notes}; {ai_note}",
    )
