"""Стейджинг результата валидации сделок."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine
from etl.models import Window

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_VALIDATION_SQL = PROJECT_ROOT / "sql" / "transforms" / "price_validation.sql"

STAGING_SCHEMA = "stg"
STAGING_TABLE = f"{STAGING_SCHEMA}.price_validation"


def _to_date(value: date | datetime | str) -> date:
    """Нормализует дату из date/datetime/ISO-строки."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def extract_and_stage_window(
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    engine: Engine | None = None,
) -> str:
    """Сохраняет результат DQ-валидации в stg.price_validation.

    Окно [start_date, end_date] — обе границы включительно.
    Таблица UNLOGGED и пересоздаётся при каждом запуске, поэтому
    повторный вызов идемпотентен.

    Возвращает полное имя staging-таблицы.
    """
    window = Window(
        start_date=_to_date(start_date),
        end_date=_to_date(end_date),
    )

    query = PRICE_VALIDATION_SQL.read_text(encoding="utf-8")
    engine = engine or create_db_engine()

    with engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {STAGING_SCHEMA}")
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
        conn.execute(
            text(f"CREATE UNLOGGED TABLE {STAGING_TABLE} AS {query}"),
            {"start_date": window.start_date, "end_date": window.end_date},
        )
        conn.exec_driver_sql(f"CREATE UNIQUE INDEX {STAGING_TABLE.replace('.', '_')}_id_idx ON {STAGING_TABLE} (id)")
        conn.exec_driver_sql(f"ANALYZE {STAGING_TABLE}")

    return STAGING_TABLE
