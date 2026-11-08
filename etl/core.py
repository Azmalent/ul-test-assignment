"""Инициализация Core DWH."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from etl.db import create_db_engine, execute_sql_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_SCHEMA_SQL = PROJECT_ROOT / "sql" / "migrations" / "002_core_schema.sql"


def init_core_schema(engine: Engine | None = None) -> None:
    """Создаёт core.prices и core.ml_training_rows.

    Функция идемпотентна: повторный вызов безопасен.
    """
    execute_sql_file(engine or create_db_engine(), CORE_SCHEMA_SQL)
