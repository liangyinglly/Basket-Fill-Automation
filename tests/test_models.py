from app.models import MatchResult, ProductCandidate


def test_product_candidate_and_match_result_dataclasses():
    candidate = ProductCandidate(
        retailer="DemoMart",
        retailer_product_id="SKU-123",
        title="Organic Whole Milk 1 gal",
        price_cents=499,
        size_text="1 gal",
        url="https://example.com/product/SKU-123",
    )
    result = MatchResult(
        request_line_id="1",
        candidate=candidate,
        confidence=0.93,
        rationale="Exact size and high token overlap.",
        selected=True,
    )

    assert result.request_line_id == "1"
    assert result.candidate.retailer_product_id == "SKU-123"
    assert result.confidence == 0.93
    assert result.selected is True

