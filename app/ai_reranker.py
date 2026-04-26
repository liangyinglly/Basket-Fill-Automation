from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import BasketItemRequest, ProductCandidate


@dataclass(frozen=True)
class ScoredCandidate:
    """Candidate with deterministic score context for optional AI reranking."""

    candidate: ProductCandidate
    score: float
    match_notes: str


@dataclass(frozen=True)
class AIRerankOutcome:
    """AI reranker decision. None product id means fallback to deterministic ranking."""

    selected_product_id: str | None
    reason: str


class AIReranker(Protocol):
    """Pluggable AI reranker contract."""

    def rerank(
        self,
        *,
        request: BasketItemRequest,
        scored_candidates: list[ScoredCandidate],
    ) -> AIRerankOutcome:
        """Return an optional selected product id and reasoning summary."""


def should_invoke_ai_reranker(
    scored_candidates: list[ScoredCandidate],
    *,
    close_score_delta: float = 0.05,
    weak_score_threshold: float = 0.52,
) -> tuple[bool, str]:
    """Invoke AI only when top candidates are close or all candidates are weak."""
    if len(scored_candidates) < 2:
        return (False, "insufficient_candidates")

    ordered = sorted(scored_candidates, key=lambda item: item.score, reverse=True)
    top_score = ordered[0].score
    second_score = ordered[1].score

    if (top_score - second_score) <= close_score_delta:
        return (True, f"close_scores(top_delta={top_score - second_score:.3f})")
    if top_score < weak_score_threshold:
        return (True, f"weak_candidates(top_score={top_score:.3f})")
    return (False, "deterministic_confident")

