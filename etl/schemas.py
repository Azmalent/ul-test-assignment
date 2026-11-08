"""Инициализация схем БД."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from etl.db import create_db_engine, execute_sql_script

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DQ_SCHEMA_SQL = PROJECT_ROOT / "sql" / "migrations" / "001_dq_schema.sql"
CORE_SCHEMA_SQL = PROJECT_ROOT / "sql" / "migrations" / "002_core_schema.sql"


def init_dq_schema(engine: Engine | None = None) -> None:
    """Создаёт схему DQ."""
    execute_sql_script(engine or create_db_engine(), DQ_SCHEMA_SQL)


def init_core_schema(engine: Engine | None = None) -> None:
    """Создаёт схему core."""
    execute_sql_script(engine or create_db_engine(), CORE_SCHEMA_SQL)
