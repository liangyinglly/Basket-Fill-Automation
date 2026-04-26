from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from app.ai_reranker import AIReranker
from app.config import Settings, load_settings
from app.db import (
    bootstrap_database,
    create_basket_match,
    create_basket_request,
    create_basket_run,
    get_connection,
    get_search_cache,
    update_basket_run_status,
    upsert_search_cache,
)
from app.decision import choose_best_candidate
from app.input_loader import load_basket_request
from app.models import BasketItemRequest, ProductCandidate
from app.normalize import normalize_query_string
from app.retailer_search import search_products
from app.scorer import score_candidate


def _serialize_candidates(candidates: list[ProductCandidate]) -> str:
    """Serialize candidate objects to JSON for search cache persistence."""
    return json.dumps([asdict(candidate) for candidate in candidates], separators=(",", ":"))


def _deserialize_candidates(payload: str) -> list[ProductCandidate]:
    """Deserialize candidate JSON payload from search cache."""
    raw = json.loads(payload)
    if not isinstance(raw, list):
        return []
    result: list[ProductCandidate] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            result.append(ProductCandidate(**item))
        except TypeError:
            continue
    return result


def _build_default_output_path(basket_id: str) -> Path:
    safe_id = normalize_query_string(basket_id).replace(" ", "_") or "basket"
    return Path("outputs") / f"{safe_id}_result.json"


def _resolve_candidates(
    *,
    connection,
    zip_code: str,
    query: str,
    max_pages: int,
) -> list[ProductCandidate]:
    """Get candidates from cache or retailer search, then update cache on miss."""
    cached = get_search_cache(connection, retailer_name="walmart", query=query)
    if cached is not None:
        return _deserialize_candidates(cached["response_json"])

    candidates = search_products(zip_code=zip_code, query=query, max_pages=max_pages)
    upsert_search_cache(
        connection,
        retailer_name="walmart",
        query=query,
        response_json=_serialize_candidates(candidates),
    )
    return candidates


def _item_output_dict(
    *,
    item: BasketItemRequest,
    normalized_query: str,
    decision_status: str,
    best_score: float,
    match_notes: str,
    selected_candidate: ProductCandidate | None,
) -> dict:
    return {
        "line_id": item.line_id,
        "name": item.name,
        "quantity": item.quantity,
        "unit": item.unit,
        "normalized_query": normalized_query,
        "decision": decision_status,
        "best_score": round(best_score, 4),
        "match_notes": match_notes,
        "selected_candidate": asdict(selected_candidate) if selected_candidate else None,
    }


def run_basket_fill(
    *,
    basket_path: str | Path,
    output_path: str | Path | None = None,
    max_pages: int = 2,
    settings: Settings | None = None,
    enable_ai_reranker: bool = False,
    ai_reranker: AIReranker | None = None,
) -> Path:
    """Run the full basket-fill flow and write the final output JSON report."""
    runtime_settings = settings or load_settings()
    bootstrap_database(runtime_settings)

    payload = load_basket_request(basket_path)
    output_file = Path(output_path) if output_path else _build_default_output_path(payload.basket_id)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(runtime_settings.db_path) as connection:
        run_id = create_basket_run(
            connection,
            basket_id=payload.basket_id,
            status="started",
            notes=f"retailer={payload.retailer}, zip={payload.zip_code}",
        )

        report_items: list[dict] = []
        try:
            for item in payload.items:
                normalized_query = normalize_query_string(item.name)
                request_id = create_basket_request(
                    connection,
                    run_id=run_id,
                    line_id=item.line_id,
                    requested_name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    normalized_name=normalized_query,
                )

                candidates = _resolve_candidates(
                    connection=connection,
                    zip_code=payload.zip_code,
                    query=normalized_query,
                    max_pages=max_pages,
                )
                decision = choose_best_candidate(
                    item,
                    candidates,
                    enable_ai_reranker=enable_ai_reranker,
                    ai_reranker=ai_reranker,
                )
                selected_candidate_id = (
                    decision.best_match.candidate.retailer_product_id
                    if decision.best_match is not None
                    else None
                )

                for candidate in candidates:
                    breakdown = score_candidate(item, candidate)
                    create_basket_match(
                        connection,
                        request_id=request_id,
                        retailer_name=candidate.retailer,
                        retailer_product_id=candidate.retailer_product_id,
                        product_title=candidate.title,
                        price_cents=candidate.price_cents,
                        confidence=breakdown.total_score,
                        rationale=breakdown.match_notes,
                        selected=(candidate.retailer_product_id == selected_candidate_id),
                    )

                report_items.append(
                    _item_output_dict(
                        item=item,
                        normalized_query=normalized_query,
                        decision_status=decision.status,
                        best_score=decision.best_score,
                        match_notes=decision.match_notes,
                        selected_candidate=(
                            decision.best_match.candidate if decision.best_match else None
                        ),
                    )
                )

            update_basket_run_status(connection, run_id=run_id, status="completed")
        except Exception:
            update_basket_run_status(connection, run_id=run_id, status="failed")
            raise

    output_payload = {
        "basket_id": payload.basket_id,
        "retailer": payload.retailer,
        "zip_code": payload.zip_code,
        "run_id": run_id,
        "status": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": report_items,
    }
    output_file.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    return output_file
