import json
from pathlib import Path
import sqlite3

from app.basket_service import run_basket_fill
from app.config import Settings
from app.models import ProductCandidate


def test_run_basket_fill_integration_with_mocked_retailer_search(
    tmp_path: Path, monkeypatch
):
    basket_path = tmp_path / "basket.json"
    basket_path.write_text(
        json.dumps(
            {
                "basket_id": "basket-integration-1",
                "retailer": "Walmart",
                "zip_code": "15213",
                "items": [
                    {"line_id": "1", "name": "Whole milk", "quantity": 1, "unit": "gallon"},
                    {"line_id": "2", "name": "Large eggs", "quantity": 12, "unit": "count"},
                ],
            }
        ),
        encoding="utf-8",
    )

    settings = Settings(
        app_env="test",
        log_level="DEBUG",
        db_path=tmp_path / "service.db",
        sql_schema_path=Path("sql/schema.sql").resolve(),
        playwright_headless=True,
    )

    search_call_count = {"count": 0}

    def fake_search_products(zip_code: str, query: str, max_pages: int = 2):
        assert zip_code == "15213"
        assert max_pages == 1
        search_call_count["count"] += 1
        if query == "whole milk":
            return [
                ProductCandidate(
                    retailer="walmart",
                    retailer_product_id="MILK-1G",
                    title="Whole Milk 1 gal",
                    size_text="1 gal",
                    price_cents=349,
                    product_url="https://www.walmart.com/ip/Whole-Milk/11111",
                    image_url="https://i5.walmartimages.com/milk.jpg",
                    url="https://www.walmart.com/ip/Whole-Milk/11111",
                )
            ]
        if query == "large eggs":
            return [
                ProductCandidate(
                    retailer="walmart",
                    retailer_product_id="EGGS-12",
                    title="Large Eggs 12 count",
                    size_text="12 count",
                    price_cents=299,
                    product_url="https://www.walmart.com/ip/Large-Eggs/22222",
                    image_url="https://i5.walmartimages.com/eggs.jpg",
                    url="https://www.walmart.com/ip/Large-Eggs/22222",
                )
            ]
        return []

    monkeypatch.setattr("app.basket_service.search_products", fake_search_products)

    output_path_first = tmp_path / "result-first.json"
    output_path_second = tmp_path / "result-second.json"

    run_basket_fill(
        basket_path=basket_path,
        output_path=output_path_first,
        max_pages=1,
        settings=settings,
    )
    first_calls = search_call_count["count"]

    run_basket_fill(
        basket_path=basket_path,
        output_path=output_path_second,
        max_pages=1,
        settings=settings,
    )

    assert first_calls == 2
    assert search_call_count["count"] == 2

    output = json.loads(output_path_second.read_text(encoding="utf-8"))
    assert output["status"] == "completed"
    assert len(output["items"]) == 2
    assert output["items"][0]["selected_candidate"]["retailer_product_id"] == "MILK-1G"
    assert output["items"][1]["selected_candidate"]["retailer_product_id"] == "EGGS-12"

    with sqlite3.connect(settings.db_path) as connection:
        runs_count = connection.execute("SELECT COUNT(*) FROM basket_runs;").fetchone()[0]
        requests_count = connection.execute("SELECT COUNT(*) FROM basket_requests;").fetchone()[0]
        matches_count = connection.execute("SELECT COUNT(*) FROM basket_matches;").fetchone()[0]
        cache_count = connection.execute("SELECT COUNT(*) FROM search_cache;").fetchone()[0]

    assert runs_count == 2
    assert requests_count == 4
    assert matches_count == 4
    assert cache_count == 2

