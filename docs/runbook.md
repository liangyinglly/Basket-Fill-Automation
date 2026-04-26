# Basket-Fill Runbook

## Purpose

Operational steps for local development, execution, and troubleshooting.

## Environment Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
cp .env.example .env
```

## Database Initialization

```bash
python -m app init-db
```

Expected outcome:
- SQLite DB file exists at `DB_PATH` (default `outputs/basket_fill.db`).
- Required tables are present (`basket_runs`, `basket_requests`, `basket_matches`, `search_cache`).

## Run Commands

Show config:
```bash
python -m app show-config
```

Run search command:
```bash
python -m app search --basket-path sample-basket.json
```

Run full basket service:
```bash
python - <<'PY'
from app.basket_service import run_basket_fill
output_path = run_basket_fill(basket_path="sample-basket.json", max_pages=2)
print(output_path)
PY
```

Run tests:
```bash
pytest -q
```

## Common Issues

### `python3.11: command not found`

- Install Python 3.11 or use temporary fallback Python for local dev.
- Keep deployment/runtime pinned to 3.11.

### Playwright browser missing

Symptom:
- errors about missing executable under Playwright cache path.

Fix:
```bash
playwright install
```

### Search is slow or failing intermittently

- Reduce `max_pages` for lower latency.
- Verify network connectivity and Walmart page availability.
- Retry; adapter already includes timeout/retry/backoff.

### Empty candidates for valid query

- Confirm ZIP code format and query normalization.
- Check whether Walmart layout/selectors changed.
- Inspect logs from `app.retailer_search`.

## Data Inspection

Inspect cached searches:
```sql
SELECT retailer_name, query, fetched_at, expires_at
FROM search_cache
ORDER BY fetched_at DESC
LIMIT 20;
```

Inspect latest run status:
```sql
SELECT id, basket_id, status, started_at, completed_at
FROM basket_runs
ORDER BY id DESC
LIMIT 5;
```

Inspect selected matches:
```sql
SELECT br.id AS run_id, bq.line_id, bm.retailer_product_id, bm.confidence
FROM basket_runs br
JOIN basket_requests bq ON bq.run_id = br.id
JOIN basket_matches bm ON bm.request_id = bq.id
WHERE bm.selected = 1
ORDER BY br.id DESC, bq.id;
```
