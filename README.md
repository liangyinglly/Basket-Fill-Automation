# Grocery Basket-Fill Assessment (Python 3.11)

CLI-first starter project for a grocery basket-fill coding assessment.

## Setup

- Use Python `3.12`.
- Create a virtual environment and install dependencies:
  - `python3.11 -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and adjust values as needed.
- Initialize the SQLite database:
  - `python -m app init-db`

## Architecture

- `app/`: application source code (CLI, config, database bootstrap).
- `sql/`: SQL schema and migration bootstrap assets.
- `tests/`: unit and smoke tests.
- `docs/`: design notes and assessment write-ups.
- `outputs/`: runtime outputs (SQLite file, generated artifacts).

## Matching Logic

- Placeholder section for basket item normalization and matching pipeline.
- Placeholder section for candidate generation and scoring.
- Placeholder section for tie-breakers and fallback handling.
- Optional AI reranker exists but is disabled by default.
- AI reranker invocation rule:
  - only when top candidate scores are close, or when all candidates are weak.
- Decision `match_notes` always records whether AI was invoked and the reason.
- If AI is unavailable or errors, the system falls back to deterministic ranking.

## Tradeoffs

- Placeholder section for implementation tradeoffs (accuracy vs latency, complexity vs maintainability).
- Placeholder section for data quality and determinism tradeoffs.

## Scale/Cost Strategy

- Placeholder section for batching, caching, and request minimization.
- Placeholder section for operational and infra cost controls.
