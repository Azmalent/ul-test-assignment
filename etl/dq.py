"""Инициализация схемы карантина DQ."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine, execute_sql_file
from etl.models import DqReason

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DQ_SCHEMA_SQL = PROJECT_ROOT / "sql" / "migrations" / "001_dq_schema.sql"


def init_dq_schema(engine: Engine | None = None) -> None:
    """Создаёт схему dq, справочник причин и таблицу карантина.

    Функция идемпотентна: повторный вызов безопасен.
    Если engine не передан, создаётся из DATABASE_URL /
    AIRFLOW_CONN_DEALS_BIGDATA.
    """
    execute_sql_file(engine or create_db_engine(), DQ_SCHEMA_SQL)


def get_dq_reasons(engine: Engine | None = None) -> list[DqReason]:
    """Читает и валидирует справочник причин отсева."""
    engine = engine or create_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, description FROM dq.dq_quarantine_reasons ORDER BY id")
        ).mappings().all()
    return [DqReason.model_validate(dict(row)) for row in rows]
