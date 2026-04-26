# Basket-Fill Architecture

## System Overview

The project is a CLI-first basket-fill pipeline:

1. Load and validate basket input JSON.
2. Normalize query strings per basket item.
3. Resolve product candidates from cache or Walmart search.
4. Score and select best candidate deterministically.
5. Optionally rerank ambiguous cases with AI (disabled by default).
6. Persist run data and emit output JSON artifact.

## Module Responsibilities

- `app/cli.py`
  - Entry commands: `init-db`, `show-config`, `search`.
- `app/input_loader.py`
  - Validates retailer, ZIP, and item schema.
- `app/normalize.py`
  - Provides stable text normalization for search/matching.
- `app/retailer_search.py`
  - Walmart Playwright adapter with timeout, retry/backoff, and throttling.
- `app/scorer.py`
  - Deterministic weighted scoring with explainable factor breakdown.
- `app/decision.py`
  - Threshold-based classification (`exact_match`, `substitute`, `unmatched`).
  - Optional AI reranker integration via pluggable interface.
- `app/ai_reranker.py`
  - AI reranker protocol + AI invocation gating rules.
- `app/db.py`
  - SQLite bootstrap and CRUD for runs, requests, matches, and search cache.
- `app/basket_service.py`
  - End-to-end orchestration and final JSON output generation.

## Data Flow

1. Input file -> `BasketRequestPayload`.
2. For each item:
  - normalized query generated
  - cache lookup on `(retailer, query)`
  - cache miss triggers Walmart search
3. Candidates scored and decision selected.
4. Persistence writes:
  - `basket_runs`
  - `basket_requests`
  - `basket_matches`
  - `search_cache` (on miss)
5. Final report written to `outputs/*.json`.

## Persistence Model

- `basket_runs`: one row per run, status + lifecycle fields.
- `basket_requests`: requested basket lines for a run.
- `basket_matches`: candidate-level scoring and selected flag.
- `search_cache`: cached candidate payload per `(retailer_name, query)`.

## Deterministic vs AI-Assisted Decisioning

- Deterministic scoring/decision is the default and primary path.
- AI reranker is optional and invoked only for uncertain cases.
- If AI is not configured or fails, deterministic ranking remains authoritative.

## Reliability Notes

- Input validation fails fast with clear errors.
- Retailer adapter tolerates missing optional fields.
- Timeouts/retries/backoff reduce transient scrape failures.
- Decision output includes `match_notes` for traceability.
