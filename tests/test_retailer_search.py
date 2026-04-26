from app.retailer_search import (
    _build_candidate,
    _extract_product_id,
    _extract_size_text,
    _parse_price_to_cents,
    _with_retry,
)


def test_parse_price_to_cents():
    assert _parse_price_to_cents("$3.49") == 349
    assert _parse_price_to_cents("3") == 300
    assert _parse_price_to_cents("$12.5") == 1250
    assert _parse_price_to_cents(None) is None
    assert _parse_price_to_cents("not-a-price") is None


def test_extract_size_text_prefers_explicit_value_then_title():
    assert _extract_size_text("Whole Milk 1 gal", "1 gal") == "1 gal"
    assert _extract_size_text("Large Eggs 12 count", None) == "12 count"
    assert _extract_size_text("Organic Bananas", None) is None


def test_extract_product_id_uses_fallback_then_url():
    assert (
        _extract_product_id("https://www.walmart.com/ip/Whole-Milk/12345678", "SKU-1")
        == "SKU-1"
    )
    assert (
        _extract_product_id("https://www.walmart.com/ip/Whole-Milk/12345678", None)
        == "12345678"
    )


def test_build_candidate_handles_missing_optional_fields():
    candidate = _build_candidate(
        title="Whole Milk 1 gal",
        product_url=None,
        image_url=None,
        price_text=None,
        size_text_raw=None,
        product_id_raw="MILK-1",
    )

    assert candidate is not None
    assert candidate.title == "Whole Milk 1 gal"
    assert candidate.price_cents is None
    assert candidate.size_text == "1 gal"
    assert candidate.product_url is None
    assert candidate.image_url is None


def test_build_candidate_returns_none_when_title_missing():
    assert (
        _build_candidate(
            title=None,
            product_url="https://www.walmart.com/ip/item/123",
            image_url=None,
            price_text="$1.99",
            size_text_raw=None,
            product_id_raw="123",
        )
        is None
    )


def test_with_retry_recovers_after_transient_error():
    call_count = {"count": 0}

    def flaky() -> int:
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise RuntimeError("temporary")
        return 42

    # _with_retry catches Playwright errors in production path; this test validates
    # deterministic retry behavior by using a compatible wrapper.
    def wrapped_flaky() -> int:
        try:
            return flaky()
        except RuntimeError as exc:
            from playwright.sync_api import Error as PlaywrightError

            raise PlaywrightError(str(exc))

    assert _with_retry(wrapped_flaky, attempts=4, base_backoff_seconds=0.0) == 42

