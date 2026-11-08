"""Инициализация схемы core."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from etl.db import create_db_engine, execute_sql_script

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_SCHEMA_SQL = PROJECT_ROOT / "sql" / "migrations" / "002_core_schema.sql"


def init_core_schema(engine: Engine | None = None) -> None:
    """Создаёт схему core."""
    execute_sql_script(engine or create_db_engine(), CORE_SCHEMA_SQL)
