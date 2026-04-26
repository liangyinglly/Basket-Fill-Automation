from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback only used pre-install
    def load_dotenv(path: Path) -> bool:
        if not path.exists():
            return False
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        return True


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    db_path: Path
    sql_schema_path: Path
    playwright_headless: bool


def _parse_bool(value: str, *, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def load_settings(env_file: str | Path | None = None) -> Settings:
    if env_file is None:
        default_env = Path(".env")
        if default_env.exists():
            load_dotenv(default_env)
    else:
        load_dotenv(Path(env_file))

    db_path = Path(os.getenv("DB_PATH", "outputs/basket_fill.db"))
    schema_path = Path(os.getenv("SQL_SCHEMA_PATH", "sql/schema.sql"))

    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        db_path=db_path,
        sql_schema_path=schema_path,
        playwright_headless=_parse_bool(
            os.getenv("PLAYWRIGHT_HEADLESS", "true"),
            default=True,
        ),
    )
