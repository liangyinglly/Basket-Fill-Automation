from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class BasketItemRequest:
    """Represents one requested item in the incoming basket payload."""

    line_id: str
    name: str
    quantity: float
    unit: str


@dataclass(frozen=True)
class ProductCandidate:
    """Represents one retailer product candidate produced by search."""

    retailer: str
    retailer_product_id: str
    title: str
    price_cents: int | None = None
    size_text: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class MatchResult:
    """Represents match-scoring output for one requested basket item."""

    request_line_id: str
    candidate: ProductCandidate
    confidence: float
    rationale: str | None = None
    selected: bool = False


@dataclass(frozen=True)
class BasketRequestPayload:
    """Validated, typed request payload loaded from the basket input JSON."""

    basket_id: str
    retailer: str
    zip_code: str
    items: tuple[BasketItemRequest, ...]

    @classmethod
    def from_iterable(
        cls,
        *,
        basket_id: str,
        retailer: str,
        zip_code: str,
        items: Iterable[BasketItemRequest],
    ) -> "BasketRequestPayload":
        """Build a payload instance from any iterable of item requests."""
        return cls(
            basket_id=basket_id,
            retailer=retailer,
            zip_code=zip_code,
            items=tuple(items),
        )

