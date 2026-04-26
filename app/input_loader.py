from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from app.models import BasketItemRequest, BasketRequestPayload


_RETAILER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{1,63}$")
_ZIP_RE = re.compile(r"^\d{5}(?:-\d{4})?$")


def validate_retailer(retailer: str) -> str:
    """Validate and normalize retailer name from input payload."""
    cleaned = retailer.strip()
    if not _RETAILER_RE.fullmatch(cleaned):
        raise ValueError(
            "Invalid retailer. Use 2-64 characters: letters, numbers, spaces, '_' or '-'."
        )
    return cleaned


def validate_zip(zip_code: str) -> str:
    """Validate US ZIP code format (12345 or 12345-6789)."""
    cleaned = zip_code.strip()
    if not _ZIP_RE.fullmatch(cleaned):
        raise ValueError("Invalid zip code. Expected '12345' or '12345-6789'.")
    return cleaned


def validate_items(items: Any) -> list[BasketItemRequest]:
    """Validate list of basket items and return typed item models."""
    if not isinstance(items, list) or len(items) == 0:
        raise ValueError("Invalid items. Expected a non-empty list.")

    typed_items: list[BasketItemRequest] = []
    seen_line_ids: set[str] = set()

    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise ValueError("Invalid item. Each item must be an object.")

        line_id = str(raw_item.get("line_id", "")).strip()
        name = str(raw_item.get("name", "")).strip()
        unit = str(raw_item.get("unit", "")).strip()
        notes_raw = raw_item.get("notes")
        preferred_brand_raw = raw_item.get("preferred_brand")
        quantity_raw = raw_item.get("quantity")

        if not line_id:
            raise ValueError("Invalid item line_id. It must be non-empty.")
        if line_id in seen_line_ids:
            raise ValueError(f"Duplicate line_id detected: {line_id}")
        seen_line_ids.add(line_id)

        if not name:
            raise ValueError(f"Invalid item name for line_id={line_id}.")
        if not unit:
            raise ValueError(f"Invalid item unit for line_id={line_id}.")

        if not isinstance(quantity_raw, (int, float)):
            raise ValueError(f"Invalid quantity for line_id={line_id}. Must be numeric.")
        quantity = float(quantity_raw)
        if quantity <= 0:
            raise ValueError(f"Invalid quantity for line_id={line_id}. Must be > 0.")

        typed_items.append(
            BasketItemRequest(
                line_id=line_id,
                name=name,
                quantity=quantity,
                unit=unit,
                notes=str(notes_raw).strip() if notes_raw is not None else None,
                preferred_brand=(
                    str(preferred_brand_raw).strip()
                    if preferred_brand_raw is not None
                    else None
                ),
            )
        )

    return typed_items


def load_basket_request(path: str | Path) -> BasketRequestPayload:
    """Load and validate a basket request JSON payload from disk."""
    basket_path = Path(path)
    raw = json.loads(basket_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid basket JSON. Top-level payload must be an object.")

    basket_id = str(raw.get("basket_id", "")).strip()
    if not basket_id:
        raise ValueError("Invalid basket_id. It must be non-empty.")

    retailer = validate_retailer(str(raw.get("retailer", "")))
    zip_code = validate_zip(str(raw.get("zip_code", "")))
    items = validate_items(raw.get("items"))

    return BasketRequestPayload.from_iterable(
        basket_id=basket_id,
        retailer=retailer,
        zip_code=zip_code,
        items=items,
    )
