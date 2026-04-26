from app.ai_reranker import AIRerankOutcome, ScoredCandidate, should_invoke_ai_reranker
from app.decision import choose_best_candidate
from app.models import BasketItemRequest, ProductCandidate


class _FixedReranker:
    def __init__(self, selected_product_id: str | None, reason: str = "ai_selected"):
        self.selected_product_id = selected_product_id
        self.reason = reason
        self.calls = 0

    def rerank(self, *, request, scored_candidates):
        self.calls += 1
        return AIRerankOutcome(
            selected_product_id=self.selected_product_id,
            reason=self.reason,
        )


class _FailingReranker:
    def rerank(self, *, request, scored_candidates):
        raise RuntimeError("provider unavailable")


def test_should_invoke_ai_reranker_rules():
    close = [
        ScoredCandidate(
            candidate=ProductCandidate("walmart", "A", "Item A"),
            score=0.50,
            match_notes="",
        ),
        ScoredCandidate(
            candidate=ProductCandidate("walmart", "B", "Item B"),
            score=0.47,
            match_notes="",
        ),
    ]
    weak = [
        ScoredCandidate(
            candidate=ProductCandidate("walmart", "A", "Item A"),
            score=0.40,
            match_notes="",
        ),
        ScoredCandidate(
            candidate=ProductCandidate("walmart", "B", "Item B"),
            score=0.20,
            match_notes="",
        ),
    ]
    confident = [
        ScoredCandidate(
            candidate=ProductCandidate("walmart", "A", "Item A"),
            score=0.90,
            match_notes="",
        ),
        ScoredCandidate(
            candidate=ProductCandidate("walmart", "B", "Item B"),
            score=0.70,
            match_notes="",
        ),
    ]

    should_close, close_reason = should_invoke_ai_reranker(close)
    should_weak, weak_reason = should_invoke_ai_reranker(weak)
    should_confident, confident_reason = should_invoke_ai_reranker(confident)

    assert should_close is True
    assert close_reason.startswith("close_scores")
    assert should_weak is True
    assert weak_reason.startswith("weak_candidates")
    assert should_confident is False
    assert confident_reason == "deterministic_confident"


def test_choose_best_candidate_ai_disabled_by_default():
    request = BasketItemRequest(line_id="1", name="Whole milk", quantity=1, unit="gallon")
    candidates = [
        ProductCandidate("walmart", "MILK-A", "Whole Milk 1 gal", size_text="1 gal"),
        ProductCandidate("walmart", "MILK-B", "Whole Milk 0.5 gal", size_text="0.5 gal"),
    ]
    reranker = _FixedReranker(selected_product_id="MILK-B")

    decision = choose_best_candidate(request, candidates)

    assert decision.best_match is not None
    assert decision.best_match.candidate.retailer_product_id == "MILK-A"
    assert reranker.calls == 0
    assert "ai_invoked=false reason=disabled" in decision.match_notes


def test_choose_best_candidate_uses_ai_when_scores_are_close():
    request = BasketItemRequest(line_id="2", name="Greek yogurt", quantity=32, unit="oz")
    candidates = [
        ProductCandidate("walmart", "YOG-A", "Greek Yogurt Plain 32 oz", size_text="32 oz"),
        ProductCandidate("walmart", "YOG-B", "Plain Greek Yogurt 32 oz", size_text="32 oz"),
    ]
    reranker = _FixedReranker(selected_product_id="YOG-B", reason="brand-policy")

    decision = choose_best_candidate(
        request,
        candidates,
        enable_ai_reranker=True,
        ai_reranker=reranker,
    )

    assert reranker.calls == 1
    assert decision.best_match is not None
    assert decision.best_match.candidate.retailer_product_id == "YOG-B"
    assert "ai_invoked=true" in decision.match_notes
    assert "reason=close_scores" in decision.match_notes


def test_choose_best_candidate_fallback_when_ai_unavailable():
    request = BasketItemRequest(line_id="3", name="Greek yogurt", quantity=32, unit="oz")
    candidates = [
        ProductCandidate("walmart", "YOG-A", "Greek Yogurt Plain 32 oz", size_text="32 oz"),
        ProductCandidate("walmart", "YOG-B", "Plain Greek Yogurt 32 oz", size_text="32 oz"),
    ]

    deterministic = choose_best_candidate(request, candidates)
    decision = choose_best_candidate(
        request,
        candidates,
        enable_ai_reranker=True,
        ai_reranker=_FailingReranker(),
    )

    assert decision.best_match is not None
    assert deterministic.best_match is not None
    assert (
        decision.best_match.candidate.retailer_product_id
        == deterministic.best_match.candidate.retailer_product_id
    )
    assert "ai_error_fallback" in decision.match_notes
