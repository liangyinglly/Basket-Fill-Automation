# Scale and Cost Strategy

## Goals

- Keep matching quality stable under growth.
- Keep deterministic path as default for predictable behavior and cost.
- Minimize repeated retailer scraping/API usage.

## How To Avoid Re-Solving Identical Queries

- Normalize every item name to a stable query string.
- Use `(retailer_name, query)` as cache key.
- Check cache before running Walmart search.
- Return cached candidates directly on hit.
- Persist cache in `search_cache` so all runs can reuse prior results.

## What Is Cached

- Cached artifact:
  - normalized `ProductCandidate` list serialized as JSON.
- Cache metadata:
  - `retailer_name`
  - `query`
  - `response_json`
  - `fetched_at`
  - optional `expires_at`
- Cache storage:
  - SQLite table `search_cache`.

## Deterministic vs AI-Assisted

- Deterministic (default/happy path):
  - scoring with fixed weighted factors
  - threshold-based decisioning
  - no AI dependency
- AI-assisted (optional):
  - only invoked when candidates are close in score or all weak
  - pluggable reranker interface
  - fallback to deterministic if AI is disabled/unavailable/errors
- Traceability:
  - `match_notes` records whether AI ran and why.

## Scale to 5,000 Users

For 5,000 active users, move from single-process local mode to service mode:

1. Split into API workers + async job workers.
2. Queue basket runs (e.g., Redis/SQS) to smooth bursts.
3. Move DB from SQLite to managed Postgres for concurrent writes.
4. Keep shared cache in Redis/Postgres table with TTL.
5. Partition work by retailer/query and deduplicate in-flight fetches.
6. Add horizontal worker autoscaling using queue depth and latency SLOs.
7. Add observability:
  - cache hit rate
  - search latency
  - reranker invocation rate
  - cost per basket.

## Controlling Proxy/API/Search Costs

- Max page cap:
  - keep `max_pages` small by default.
- Cache-first policy:
  - avoid repeated scrape/API calls for the same normalized query.
- TTL strategy:
  - longer TTL for stable pantry items
  - shorter TTL for volatile categories/pricing.
- Batch and dedupe:
  - coalesce identical queries across concurrent requests.
- Progressive retrieval:
  - fetch first page first; only fetch more if confidence remains low.
- AI invocation guardrails:
  - AI reranker only on uncertain cases.
- Budget controls:
  - enforce per-run and per-day query budgets.
  - degrade gracefully to deterministic-only mode when budget is exceeded.

## Practical Defaults

- Deterministic mode enabled.
- AI reranker disabled.
- Cache enabled for all retailer query responses.
- Conservative page depth and retry counts.
- Alert when cache hit rate drops or scrape retries spike.
