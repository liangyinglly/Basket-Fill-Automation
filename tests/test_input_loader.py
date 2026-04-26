import json
from pathlib import Path

import pytest

from app.input_loader import (
    load_basket_request,
    validate_items,
    validate_retailer,
    validate_zip,
)
from app.models import BasketItemRequest
from app.normalize import normalize_query_string


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    target = tmp_path / "basket.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_load_basket_request_valid_payload(tmp_path: Path):
    payload_path = _write_payload(
        tmp_path,
        {
            "basket_id": "basket-001",
            "retailer": "DemoMart",
            "zip_code": "15213",
            "items": [
                {"line_id": "1", "name": "Organic Whole Milk", "quantity": 1, "unit": "gallon"},
                {"line_id": "2", "name": "Bananas", "quantity": 6, "unit": "count"},
            ],
        },
    )

    result = load_basket_request(payload_path)

    assert result.basket_id == "basket-001"
    assert result.retailer == "DemoMart"
    assert result.zip_code == "15213"
    assert len(result.items) == 2
    assert result.items[0] == BasketItemRequest(
        line_id="1",
        name="Organic Whole Milk",
        quantity=1.0,
        unit="gallon",
    )


@pytest.mark.parametrize(
    "retailer",
    ["", " ", "@bad-store", "a", "x" * 65],
)
def test_validate_retailer_invalid(retailer: str):
    with pytest.raises(ValueError):
        validate_retailer(retailer)


@pytest.mark.parametrize(
    "zip_code",
    ["", "1521", "152131", "ABCDE", "15213-123", "15-213"],
)
def test_validate_zip_invalid(zip_code: str):
    with pytest.raises(ValueError):
        validate_zip(zip_code)


def test_validate_items_invalid_cases():
    with pytest.raises(ValueError):
        validate_items([])

    with pytest.raises(ValueError):
        validate_items([{"line_id": "1", "name": "", "quantity": 1, "unit": "count"}])

    with pytest.raises(ValueError):
        validate_items([{"line_id": "1", "name": "Eggs", "quantity": 0, "unit": "dozen"}])

    with pytest.raises(ValueError):
        validate_items(
            [
                {"line_id": "1", "name": "Eggs", "quantity": 1, "unit": "dozen"},
                {"line_id": "1", "name": "Milk", "quantity": 1, "unit": "gallon"},
            ]
        )


def test_normalize_query_string():
    assert normalize_query_string("  Organic Whole-Milk!!! ") == "organic whole milk"
    assert normalize_query_string("Eggs, Large (12ct)") == "eggs large 12ct"

