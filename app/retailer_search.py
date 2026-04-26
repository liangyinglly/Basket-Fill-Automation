from __future__ import annotations

import logging
import re
import time
from typing import Callable, TypeVar
from urllib.parse import quote_plus

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Locator, sync_playwright

from app.models import BasketRequestPayload, ProductCandidate


logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_PRICE_RE = re.compile(r"\$?\s*(\d+)(?:\.(\d{1,2}))?")
_SIZE_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(gallon|gal|dozen|count|ct|lb|pound|oz|ounce)s?\b",
    re.IGNORECASE,
)
_PRODUCT_ID_IN_URL_RE = re.compile(r"/(\d{5,})\b")


def _safe_inner_text(locator: Locator) -> str | None:
    try:
        text = locator.first.inner_text(timeout=1000).strip()
        return text or None
    except PlaywrightError:
        return None


def _safe_attr(locator: Locator, attr_name: str) -> str | None:
    try:
        value = locator.first.get_attribute(attr_name, timeout=1000)
        if value is None:
            return None
        value = value.strip()
        return value or None
    except PlaywrightError:
        return None


def _parse_price_to_cents(price_text: str | None) -> int | None:
    if not price_text:
        return None
    match = _PRICE_RE.search(price_text)
    if match is None:
        return None
    dollars = int(match.group(1))
    cents_raw = match.group(2)
    cents = 0 if cents_raw is None else int(cents_raw.ljust(2, "0"))
    return dollars * 100 + cents


def _extract_size_text(title: str, size_text: str | None) -> str | None:
    if size_text and size_text.strip():
        return size_text.strip()
    match = _SIZE_RE.search(title)
    if match is None:
        return None
    return f"{match.group(1)} {match.group(2).lower()}"


def _extract_product_id(product_url: str | None, fallback_id: str | None) -> str:
    if fallback_id and fallback_id.strip():
        return fallback_id.strip()
    if product_url:
        match = _PRODUCT_ID_IN_URL_RE.search(product_url)
        if match:
            return match.group(1)
    return f"unknown-{int(time.time() * 1000)}"


def _build_candidate(
    *,
    title: str | None,
    product_url: str | None,
    image_url: str | None,
    price_text: str | None,
    size_text_raw: str | None,
    product_id_raw: str | None,
) -> ProductCandidate | None:
    """Normalize extracted text fields into a ProductCandidate model."""
    if not title or not title.strip():
        return None
    clean_title = title.strip()
    product_id = _extract_product_id(product_url, product_id_raw)
    size_text = _extract_size_text(title=clean_title, size_text=size_text_raw)

    return ProductCandidate(
        retailer="walmart",
        retailer_product_id=product_id,
        title=clean_title,
        price_cents=_parse_price_to_cents(price_text),
        size_text=size_text,
        product_url=product_url,
        image_url=image_url,
        url=product_url,
    )


def _with_retry(
    func: Callable[[], _T],
    *,
    attempts: int = 3,
    base_backoff_seconds: float = 1.0,
) -> _T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            sleep_seconds = base_backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Walmart call failed (attempt %s/%s): %s. Retrying in %.1fs",
                attempt,
                attempts,
                exc,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)
    assert last_error is not None
    raise last_error


def _extract_candidate_from_card(card: Locator) -> ProductCandidate | None:
    title = _safe_inner_text(
        card.locator("[data-automation-id='product-title'], a[data-automation-id='product-title']")
    )
    if not title:
        return None

    link = card.locator("a[href*='/ip/'], a[data-automation-id='product-title']")
    href = _safe_attr(link, "href")
    if href and href.startswith("/"):
        product_url = f"https://www.walmart.com{href}"
    else:
        product_url = href

    image_url = _safe_attr(card.locator("img"), "src")
    size_text_raw = _safe_inner_text(
        card.locator("[data-testid='product-variant-size'], [data-automation-id='product-size']")
    )

    price_text = _safe_inner_text(
        card.locator(
            "[data-automation-id='product-price'], [itemprop='price'], span[class*='price']"
        )
    )
    product_id_raw = _safe_attr(card, "data-item-id")

    return _build_candidate(
        title=title,
        product_url=product_url,
        image_url=image_url,
        price_text=price_text,
        size_text_raw=size_text_raw,
        product_id_raw=product_id_raw,
    )


def search_products(zip_code: str, query: str, max_pages: int = 2) -> list[ProductCandidate]:
    """Search Walmart with Playwright and return normalized product candidates."""
    timeout_ms = 15000
    throttle_seconds = 1.0
    max_pages = max(1, max_pages)
    query_encoded = quote_plus(query.strip())
    candidates: list[ProductCandidate] = []

    logger.info(
        "Starting Walmart search for query='%s', zip_code='%s', max_pages=%s",
        query,
        zip_code,
        max_pages,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            for page_no in range(1, max_pages + 1):
                url = (
                    "https://www.walmart.com/search"
                    f"?q={query_encoded}&page={page_no}&postalCode={quote_plus(zip_code)}"
                )
                logger.info("Loading Walmart page %s: %s", page_no, url)

                try:
                    _with_retry(lambda: page.goto(url, wait_until="domcontentloaded"))
                except PlaywrightError as exc:
                    logger.error("Failed to load Walmart page %s: %s", page_no, exc)
                    break

                # Give client-side rendering a short window.
                time.sleep(0.8)

                cards = page.locator("div[data-item-id]")
                try:
                    card_count = cards.count()
                except PlaywrightError:
                    card_count = 0

                logger.info("Walmart page %s yielded %s candidate cards", page_no, card_count)

                for idx in range(card_count):
                    try:
                        candidate = _extract_candidate_from_card(cards.nth(idx))
                    except PlaywrightError as exc:
                        logger.warning("Skipping Walmart card %s on page %s: %s", idx, page_no, exc)
                        continue
                    if candidate is None:
                        continue
                    candidates.append(candidate)

                if page_no < max_pages:
                    logger.debug("Throttling %.1fs before next Walmart page", throttle_seconds)
                    time.sleep(throttle_seconds)
        finally:
            context.close()
            browser.close()

    logger.info("Walmart search complete for query='%s' with %s candidates", query, len(candidates))
    return candidates


def search_retailer_products(
    *,
    payload: BasketRequestPayload,
    queries: list[str],
    max_pages: int = 2,
) -> list[ProductCandidate]:
    """Search Walmart for all query strings and return aggregated candidates."""
    all_candidates: list[ProductCandidate] = []
    for query in queries:
        try:
            all_candidates.extend(search_products(payload.zip_code, query, max_pages=max_pages))
        except PlaywrightError as exc:
            logger.error("Walmart search failed for query='%s': %s", query, exc)
    return all_candidates
