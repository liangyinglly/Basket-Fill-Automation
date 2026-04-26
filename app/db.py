from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from app.config import Settings


def bootstrap_database(settings: Settings) -> Path:
    """Initialize the SQLite database file using the configured schema script."""
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = settings.sql_schema_path
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with sqlite3.connect(db_path) as connection:
        script = schema_path.read_text(encoding="utf-8")
        connection.executescript(script)
        connection.execute("PRAGMA foreign_keys = ON;")

    return db_path


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """Return a sqlite3 connection with foreign keys enabled and row access by name."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def create_basket_run(
    connection: sqlite3.Connection,
    *,
    basket_id: str | None,
    status: str,
    notes: str | None = None,
) -> int:
    """Insert a basket run row and return the new run ID."""
    cursor = connection.execute(
        """
        INSERT INTO basket_runs (basket_id, status, notes)
        VALUES (?, ?, ?);
        """,
        (basket_id, status, notes),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_basket_run(connection: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    """Fetch a single basket run by primary key."""
    cursor = connection.execute(
        "SELECT * FROM basket_runs WHERE id = ?;",
        (run_id,),
    )
    return cursor.fetchone()


def update_basket_run_status(
    connection: sqlite3.Connection,
    *,
    run_id: int,
    status: str,
    completed_at: str | None = None,
) -> None:
    """Update the status and optional completion timestamp for a run."""
    connection.execute(
        """
        UPDATE basket_runs
        SET status = ?, completed_at = ?
        WHERE id = ?;
        """,
        (status, completed_at, run_id),
    )
    connection.commit()


def delete_basket_run(connection: sqlite3.Connection, run_id: int) -> int:
    """Delete a basket run by ID and return the number of deleted rows."""
    cursor = connection.execute("DELETE FROM basket_runs WHERE id = ?;", (run_id,))
    connection.commit()
    return int(cursor.rowcount)


def create_basket_request(
    connection: sqlite3.Connection,
    *,
    run_id: int,
    line_id: str,
    requested_name: str,
    quantity: float,
    unit: str,
    normalized_name: str | None = None,
) -> int:
    """Insert a basket request and return the new request ID."""
    cursor = connection.execute(
        """
        INSERT INTO basket_requests
        (run_id, line_id, requested_name, quantity, unit, normalized_name)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (run_id, line_id, requested_name, quantity, unit, normalized_name),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_basket_request(
    connection: sqlite3.Connection, request_id: int
) -> sqlite3.Row | None:
    """Fetch a single basket request by primary key."""
    cursor = connection.execute(
        "SELECT * FROM basket_requests WHERE id = ?;",
        (request_id,),
    )
    return cursor.fetchone()


def update_basket_request_normalized_name(
    connection: sqlite3.Connection, *, request_id: int, normalized_name: str
) -> None:
    """Update normalized_name for a basket request."""
    connection.execute(
        "UPDATE basket_requests SET normalized_name = ? WHERE id = ?;",
        (normalized_name, request_id),
    )
    connection.commit()


def delete_basket_request(connection: sqlite3.Connection, request_id: int) -> int:
    """Delete a basket request by ID and return deleted row count."""
    cursor = connection.execute("DELETE FROM basket_requests WHERE id = ?;", (request_id,))
    connection.commit()
    return int(cursor.rowcount)


def create_basket_match(
    connection: sqlite3.Connection,
    *,
    request_id: int,
    retailer_name: str,
    retailer_product_id: str,
    product_title: str,
    confidence: float,
    price_cents: int | None = None,
    rationale: str | None = None,
    selected: bool = False,
) -> int:
    """Insert a candidate match and return the new match ID."""
    cursor = connection.execute(
        """
        INSERT INTO basket_matches
        (
            request_id,
            retailer_name,
            retailer_product_id,
            product_title,
            price_cents,
            confidence,
            rationale,
            selected
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            request_id,
            retailer_name,
            retailer_product_id,
            product_title,
            price_cents,
            confidence,
            rationale,
            int(selected),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_basket_match(connection: sqlite3.Connection, match_id: int) -> sqlite3.Row | None:
    """Fetch a single basket match by primary key."""
    cursor = connection.execute(
        "SELECT * FROM basket_matches WHERE id = ?;",
        (match_id,),
    )
    return cursor.fetchone()


def set_selected_match(
    connection: sqlite3.Connection, *, request_id: int, match_id: int
) -> None:
    """Mark one match as selected for a request and unselect all other matches."""
    connection.execute(
        "UPDATE basket_matches SET selected = 0 WHERE request_id = ?;",
        (request_id,),
    )
    connection.execute(
        "UPDATE basket_matches SET selected = 1 WHERE id = ? AND request_id = ?;",
        (match_id, request_id),
    )
    connection.commit()


def update_basket_match_confidence(
    connection: sqlite3.Connection, *, match_id: int, confidence: float
) -> None:
    """Update the confidence score for a basket match."""
    connection.execute(
        "UPDATE basket_matches SET confidence = ? WHERE id = ?;",
        (confidence, match_id),
    )
    connection.commit()


def delete_basket_match(connection: sqlite3.Connection, match_id: int) -> int:
    """Delete a basket match by ID and return deleted row count."""
    cursor = connection.execute("DELETE FROM basket_matches WHERE id = ?;", (match_id,))
    connection.commit()
    return int(cursor.rowcount)


def upsert_search_cache(
    connection: sqlite3.Connection,
    *,
    retailer_name: str,
    query: str,
    response_json: str,
    fetched_at: str | None = None,
    expires_at: str | None = None,
) -> int:
    """Insert or update cached search payload keyed by retailer/query."""
    if fetched_at is None:
        fetched_at_expr = "datetime('now')"
        fetched_at_params: tuple[Any, ...] = ()
    else:
        fetched_at_expr = "?"
        fetched_at_params = (fetched_at,)

    cursor = connection.execute(
        f"""
        INSERT INTO search_cache
        (retailer_name, query, response_json, fetched_at, expires_at)
        VALUES (?, ?, ?, {fetched_at_expr}, ?)
        ON CONFLICT(retailer_name, query)
        DO UPDATE SET
            response_json = excluded.response_json,
            fetched_at = excluded.fetched_at,
            expires_at = excluded.expires_at;
        """,
        (retailer_name, query, response_json, *fetched_at_params, expires_at),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_search_cache(
    connection: sqlite3.Connection,
    *,
    retailer_name: str,
    query: str,
) -> sqlite3.Row | None:
    """Fetch one cached search payload by retailer/query key."""
    cursor = connection.execute(
        "SELECT * FROM search_cache WHERE retailer_name = ? AND query = ?;",
        (retailer_name, query),
    )
    return cursor.fetchone()


def delete_expired_search_cache(
    connection: sqlite3.Connection, *, now_iso: str
) -> int:
    """Delete expired search cache records and return deleted row count."""
    cursor = connection.execute(
        """
        DELETE FROM search_cache
        WHERE expires_at IS NOT NULL AND expires_at <= ?;
        """,
        (now_iso,),
    )
    connection.commit()
    return int(cursor.rowcount)


def delete_search_cache(
    connection: sqlite3.Connection, *, retailer_name: str, query: str
) -> int:
    """Delete a search cache record by retailer/query key."""
    cursor = connection.execute(
        "DELETE FROM search_cache WHERE retailer_name = ? AND query = ?;",
        (retailer_name, query),
    )
    connection.commit()
    return int(cursor.rowcount)
