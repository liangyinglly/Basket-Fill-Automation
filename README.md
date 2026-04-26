# Grocery Basket-Fill Assessment

CLI-first Python project for basket-fill matching with:
- SQLite persistence
- Walmart search adapter via Playwright
- deterministic scoring + optional AI reranking
- JSON output artifacts per run

## Setup

### Prerequisites

- Python `3.11` target runtime (project requirement).
- Playwright browser binaries (for real Walmart scraping runs).

### Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
cp .env.example .env
```

If `python3.11` is not available locally, use your closest supported Python and keep production pinned to 3.11.

### Initialize database

```bash
source .venv/bin/activate
python -m app init-db
```

## Run Commands

### Show resolved config

```bash
python -m app show-config
```

### Run retailer search flow from CLI

```bash
python -m app search --basket-path sample-basket.json
```

### Run full basket-fill service and write output JSON

```bash
python - <<'PY'
from app.basket_service import run_basket_fill
path = run_basket_fill(basket_path="sample-basket.json", max_pages=2)
print(path)
PY
```

### Run tests

```bash
pytest -q
```

## Architecture

Top-level layout:
- `app/`: core application modules.
- `tests/`: unit + integration tests.
- `docs/`: architecture, runbook, and scaling/cost notes.
- `sql/`: SQLite schema bootstrap.
- `outputs/`: generated DB/output artifacts.

Core modules:
- `app/input_loader.py`: JSON loading + validation (retailer, ZIP, items).
- `app/normalize.py`: query normalization utilities.
- `app/retailer_search.py`: Walmart Playwright adapter with timeout/retry/throttle.
- `app/scorer.py`: deterministic weighted scoring.
- `app/decision.py`: deterministic decisioning + optional AI reranker hook.
- `app/ai_reranker.py`: pluggable AI reranker interface + invocation gating.
- `app/db.py`: SQLite bootstrap + CRUD helpers.
- `app/basket_service.py`: end-to-end orchestration and output generation.

## Tooling Choices

- `sqlite3` (stdlib): simple local persistence, easy inspection/debugging.
- `Playwright`: robust browser automation for dynamic retailer pages.
- `pytest`: lightweight test runner with fast feedback loop.
- `python-dotenv`: env-based local configuration.

## Matching Logic

### Deterministic scorer

Each candidate is scored with fixed weights:
- token similarity
- brand match
- size match
- notes keyword match
- mild category bias

`match_notes` stores per-factor scores and total score for explainability.

### Decision thresholds

Score classification:
- `exact_match` at or above exact threshold
- `substitute` between substitute and exact thresholds
- `unmatched` below substitute threshold

### Optional AI reranker (disabled by default)

AI reranking is attempted only when:
- top candidates are close in deterministic score, or
- all candidates are weak.

If AI is disabled, unavailable, or errors, decisioning falls back to deterministic selection. `match_notes` records whether AI was invoked and why.

## Tradeoffs

- Deterministic-first matching improves repeatability and testability, but can miss nuanced semantic equivalence.
- Playwright scraping is flexible for dynamic pages, but can be slower and more fragile than official APIs.
- SQLite is ideal for local/assessment scope, but a shared production workload eventually needs managed DB + queueing.
- Caching improves latency and cost, but stale cache windows must be managed explicitly.

## Scale/Cost Strategy

See:
- [Architecture Doc](/Users/liangying/Desktop/Basket Fill Automation/docs/architecture.md)
- [Runbook](/Users/liangying/Desktop/Basket Fill Automation/docs/runbook.md)
- [Scale and Cost Strategy](/Users/liangying/Desktop/Basket Fill Automation/docs/scale-cost-strategy.md)
