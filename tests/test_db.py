from pathlib import Path
import sqlite3

from app.config import Settings
from app.db import (
    bootstrap_database,
    create_basket_match,
    create_basket_request,
    create_basket_run,
    delete_expired_search_cache,
    get_basket_match,
    get_basket_request,
    get_basket_run,
    get_connection,
    get_search_cache,
    set_selected_match,
    upsert_search_cache,
)


def test_bootstrap_database_creates_required_tables(tmp_path: Path):
    db_path = tmp_path / "assessment.db"
    schema_path = Path("sql/schema.sql").resolve()

    settings = Settings(
        app_env="test",
        log_level="DEBUG",
        db_path=db_path,
        sql_schema_path=schema_path,
        playwright_headless=True,
    )

    actual_path = bootstrap_database(settings)

    assert actual_path == db_path
    assert db_path.exists()
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name IN (
                'basket_runs',
                'basket_requests',
                'basket_matches',
                'search_cache'
              )
            ORDER BY name;
            """
        ).fetchall()
    assert rows == [
        ("basket_matches",),
        ("basket_requests",),
        ("basket_runs",),
        ("search_cache",),
    ]


def test_insert_and_read_basket_entities(tmp_path: Path):
    db_path = tmp_path / "assessment.db"
    settings = Settings(
        app_env="test",
        log_level="DEBUG",
        db_path=db_path,
        sql_schema_path=Path("sql/schema.sql").resolve(),
        playwright_headless=True,
    )
    bootstrap_database(settings)

    with get_connection(db_path) as connection:
        run_id = create_basket_run(
            connection,
            basket_id="basket-123",
            status="started",
            notes="integration test run",
        )
        request_id = create_basket_request(
            connection,
            run_id=run_id,
            line_id="line-1",
            requested_name="Bananas",
            quantity=6,
            unit="count",
            normalized_name="banana",
        )
        match_a = create_basket_match(
            connection,
            request_id=request_id,
            retailer_name="DemoMart",
            retailer_product_id="SKU-1",
            product_title="Bananas 6 ct",
            confidence=0.86,
            price_cents=199,
        )
        match_b = create_basket_match(
            connection,
            request_id=request_id,
            retailer_name="DemoMart",
            retailer_product_id="SKU-2",
            product_title="Organic Bananas 6 ct",
            confidence=0.91,
            price_cents=249,
        )
        set_selected_match(connection, request_id=request_id, match_id=match_b)

        run = get_basket_run(connection, run_id)
        request = get_basket_request(connection, request_id)
        selected_match = get_basket_match(connection, match_b)
        unselected_match = get_basket_match(connection, match_a)

    assert run is not None
    assert run["basket_id"] == "basket-123"
    assert run["status"] == "started"

    assert request is not None
    assert request["requested_name"] == "Bananas"
    assert request["normalized_name"] == "banana"

    assert selected_match is not None
    assert selected_match["selected"] == 1
    assert unselected_match is not None
    assert unselected_match["selected"] == 0


def test_upsert_and_expire_search_cache(tmp_path: Path):
    db_path = tmp_path / "assessment.db"
    settings = Settings(
        app_env="test",
        log_level="DEBUG",
        db_path=db_path,
        sql_schema_path=Path("sql/schema.sql").resolve(),
        playwright_headless=True,
    )
    bootstrap_database(settings)

    with get_connection(db_path) as connection:
        upsert_search_cache(
            connection,
            retailer_name="DemoMart",
            query="milk",
            response_json='{"items":[{"sku":"A1"}]}',
            fetched_at="2026-01-01T10:00:00Z",
            expires_at="2026-01-01T11:00:00Z",
        )
        upsert_search_cache(
            connection,
            retailer_name="DemoMart",
            query="milk",
            response_json='{"items":[{"sku":"A2"}]}',
            fetched_at="2026-01-01T10:30:00Z",
            expires_at="2026-01-01T11:00:00Z",
        )
        cached = get_search_cache(connection, retailer_name="DemoMart", query="milk")
        deleted_count = delete_expired_search_cache(
            connection,
            now_iso="2026-01-01T12:00:00Z",
        )
        after_delete = get_search_cache(connection, retailer_name="DemoMart", query="milk")

    assert cached is not None
    assert cached["response_json"] == '{"items":[{"sku":"A2"}]}'
    assert deleted_count == 1
    assert after_delete is None
