from pathlib import Path

from app.config import load_settings


def test_load_settings_defaults(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("SQL_SCHEMA_PATH", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_HEADLESS", raising=False)

    settings = load_settings(env_file=Path("/tmp/does-not-exist.env"))

    assert settings.app_env == "dev"
    assert settings.log_level == "INFO"
    assert str(settings.db_path) == "outputs/basket_fill.db"
    assert str(settings.sql_schema_path) == "sql/schema.sql"
    assert settings.playwright_headless is True


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DB_PATH", "outputs/test.sqlite")
    monkeypatch.setenv("SQL_SCHEMA_PATH", "sql/schema.sql")
    monkeypatch.setenv("PLAYWRIGHT_HEADLESS", "false")

    settings = load_settings(env_file=Path("/tmp/does-not-exist.env"))

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert str(settings.db_path) == "outputs/test.sqlite"
    assert settings.playwright_headless is False

