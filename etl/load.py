"""Загрузка результатов DQ-валидации в core.prices и карантин."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine
from etl.models import LoadResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOAD_CORE_SQL = PROJECT_ROOT / "sql" / "transforms" / "load_core_prices.sql"
LOAD_QUARANTINE_SQL = PROJECT_ROOT / "sql" / "transforms" / "load_quarantine.sql"

STAGING_TABLE = "stg.price_validation"
CORE_TABLE = "core.prices"
QUARANTINE_TABLE = "dq.dq_quarantine_prices"


def _ensure_objects(conn, staging_table: str = STAGING_TABLE) -> None:
    """Проверяет, что staging и core созданы."""
    for table_name, hint in (
        (staging_table, "Сначала выполните stage-validation."),
        (CORE_TABLE, "Сначала выполните etl init-core."),
        (QUARANTINE_TABLE, "Сначала выполните etl init-dq."),
    ):
        exists = conn.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": table_name},
        ).scalar()
        if exists is None:
            raise RuntimeError(f"Нет таблицы {table_name}. {hint}")


def load_validation_results(engine: Engine | None = None) -> LoadResult:
    """Переносит staging в core.prices и dq.dq_quarantine_prices.

    Операция атомарная и идемпотентная:
    - удаляет из core и карантина все price_id, которые есть в staging;
    - заново вставляет валидные строки в core;
    - заново вставляет отбракованные строки в карантин.

    Такой DELETE + INSERT корректно обрабатывает переходы
    valid -> invalid, invalid -> valid и смену набора причин.
    """
    engine = engine or create_db_engine()
    run_id = uuid4()

    core_sql = LOAD_CORE_SQL.read_text(encoding="utf-8")
    quarantine_sql = LOAD_QUARANTINE_SQL.read_text(encoding="utf-8")

    with engine.begin() as conn:
        _ensure_objects(conn)

        core_deleted = conn.execute(
            text(f"DELETE FROM {CORE_TABLE} WHERE price_id IN (SELECT id FROM {STAGING_TABLE})")
        ).rowcount
        quarantine_deleted = conn.execute(
            text(f"DELETE FROM {QUARANTINE_TABLE} WHERE price_id IN (SELECT id FROM {STAGING_TABLE})")
        ).rowcount

        valid_rows = conn.execute(
            text(core_sql),
            {"etl_run_id": run_id},
        ).rowcount
        quarantined_rows = conn.execute(
            text(quarantine_sql),
            {"etl_run_id": run_id},
        ).rowcount

    return LoadResult(
        run_id=run_id,
        valid_rows=valid_rows,
        quarantined_rows=quarantined_rows,
        core_deleted=core_deleted,
        quarantine_deleted=quarantine_deleted,
    )
