from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import load_settings
from app.db import bootstrap_database
from app.retailer_search import search_retailer_products


def _cmd_init_db(_args: argparse.Namespace) -> int:
    settings = load_settings()
    db_path = bootstrap_database(settings)
    print(f"Database initialized at: {db_path}")
    return 0


def _cmd_show_config(_args: argparse.Namespace) -> int:
    settings = load_settings()
    print(
        json.dumps(
            {
                "app_env": settings.app_env,
                "log_level": settings.log_level,
                "db_path": str(settings.db_path),
                "sql_schema_path": str(settings.sql_schema_path),
                "playwright_headless": settings.playwright_headless,
            },
            indent=2,
        )
    )
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    _ = Path(args.basket_path)
    search_retailer_products()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="basket-fill",
        description="CLI scaffold for grocery basket-fill assessment.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db_parser = subparsers.add_parser("init-db", help="Initialize SQLite schema.")
    init_db_parser.set_defaults(func=_cmd_init_db)

    show_cfg_parser = subparsers.add_parser(
        "show-config", help="Print resolved runtime config."
    )
    show_cfg_parser.set_defaults(func=_cmd_show_config)

    search_parser = subparsers.add_parser(
        "search", help="Placeholder for retailer product search."
    )
    search_parser.add_argument(
        "--basket-path",
        default="sample-basket.json",
        help="Path to basket input JSON.",
    )
    search_parser.set_defaults(func=_cmd_search)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

