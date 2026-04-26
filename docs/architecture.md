# Architecture Notes

## Scope

- CLI-first workflow for local assessment execution.
- SQLite for local persistence.
- Retailer search abstraction prepared for future Playwright integration.

## Current Components

- `app/config.py`: environment/config resolution.
- `app/db.py`: schema bootstrap and DB initialization.
- `app/cli.py`: command routing (`init-db`, `show-config`, `search` placeholder).
- `sql/schema.sql`: base relational schema.

## Next Iterations

- Add retailer adapters using Playwright (without changing CLI contract).
- Add matching engine stages and persistence layer methods.
- Add richer test coverage for command workflows.

