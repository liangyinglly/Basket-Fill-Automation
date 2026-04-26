from app.decision import (
    EXACT_MATCH_THRESHOLD,
    SUBSTITUTE_THRESHOLD,
    choose_best_candidate,
    classify_score,
)
from app.models import BasketItemRequest, ProductCandidate
from app.scorer import score_candidate


def test_milk_one_gallon_exact_match():
    request = BasketItemRequest(
        line_id="1",
        name="Whole milk",
        quantity=1,
        unit="gallon",
    )
    candidates = [
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="MILK-1G",
            title="Whole Milk 1 gal",
            size_text="1 gal",
            category="dairy",
        ),
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="MILK-HALF",
            title="Whole Milk 0.5 gal",
            size_text="0.5 gal",
            category="dairy",
        ),
    ]

    decision = choose_best_candidate(request, candidates)

    assert decision.status == "exact_match"
    assert decision.best_match is not None
    assert decision.best_match.candidate.retailer_product_id == "MILK-1G"
    assert "size=" in decision.match_notes
    assert decision.best_score >= EXACT_MATCH_THRESHOLD


def test_eggs_twelve_count_exact_match_over_larger_pack():
    request = BasketItemRequest(
        line_id="2",
        name="Large eggs",
        quantity=12,
        unit="count",
    )
    candidates = [
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="EGG-12",
            title="Large Eggs 12 count",
            size_text="12 count",
            category="eggs",
        ),
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="EGG-18",
            title="Large Cage Free Eggs 18 count",
            size_text="18 count",
            category="eggs",
        ),
    ]

    decision = choose_best_candidate(request, candidates)

    assert decision.status == "exact_match"
    assert decision.best_match is not None
    assert decision.best_match.candidate.retailer_product_id == "EGG-12"


def test_greek_yogurt_brand_preference_affects_ranking():
    request = BasketItemRequest(
        line_id="3",
        name="Greek yogurt",
        quantity=32,
        unit="oz",
        notes="prefer chobani brand",
        preferred_brand="Chobani",
    )
    candidates = [
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="YOG-OIKOS",
            title="Oikos Greek Yogurt Plain 32 oz",
            brand="Oikos",
            size_text="32 oz",
            category="dairy",
        ),
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="YOG-CHOB",
            title="Chobani Greek Yogurt Plain 32 oz",
            brand="Chobani",
            size_text="32 oz",
            category="dairy",
        ),
    ]

    chobani_score = score_candidate(request, candidates[1])
    oikos_score = score_candidate(request, candidates[0])
    decision = choose_best_candidate(request, candidates)

    assert chobani_score.brand_match > oikos_score.brand_match
    assert decision.best_match is not None
    assert decision.best_match.candidate.retailer_product_id == "YOG-CHOB"
    assert "brand=" in decision.match_notes


def test_chicken_breast_boneless_skinless_notes_help():
    request = BasketItemRequest(
        line_id="4",
        name="Chicken breast",
        quantity=1,
        unit="lb",
        notes="boneless skinless",
    )
    candidates = [
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="CHK-BRST",
            title="Chicken Breast Boneless Skinless 1 lb",
            size_text="1 lb",
            category="meat",
        ),
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="CHK-THIGH",
            title="Chicken Thigh Bone-In Skin-On 1 lb",
            size_text="1 lb",
            category="meat",
        ),
    ]

    decision = choose_best_candidate(request, candidates)

    assert decision.best_match is not None
    assert decision.best_match.candidate.retailer_product_id == "CHK-BRST"
    assert "notes=" in decision.match_notes


def test_substitute_and_unmatched_threshold_classification():
    assert classify_score(EXACT_MATCH_THRESHOLD + 0.01) == "exact_match"
    assert classify_score((EXACT_MATCH_THRESHOLD + SUBSTITUTE_THRESHOLD) / 2) == "substitute"
    assert classify_score(SUBSTITUTE_THRESHOLD - 0.01) == "unmatched"


def test_unmatched_when_candidates_do_not_fit():
    request = BasketItemRequest(
        line_id="5",
        name="Whole milk",
        quantity=1,
        unit="gallon",
    )
    candidates = [
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="SOAP-1",
            title="Dish Soap Lemon 24 oz",
            size_text="24 oz",
            category="household",
        ),
        ProductCandidate(
            retailer="DemoMart",
            retailer_product_id="NAP-1",
            title="Paper Napkins 100 count",
            size_text="100 count",
            category="household",
        ),
    ]

    decision = choose_best_candidate(request, candidates)

    assert decision.status == "unmatched"
    assert decision.best_match is None
    assert "Unmatched:" in decision.match_notes

