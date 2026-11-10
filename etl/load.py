"""Загрузка результатов DQ-валидации в core.prices и карантин."""

import logging
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine
from etl.models import LoadResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOAD_CORE_SQL = PROJECT_ROOT.joinpath("sql/transforms/load_core_prices.sql")
LOAD_QUARANTINE_SQL = PROJECT_ROOT.joinpath("sql/transforms/load_quarantine.sql")

STAGING_TABLE = "stg.price_validation"
CORE_TABLE = "core.prices"
QUARANTINE_TABLE = "dq.dq_quarantine_prices"
QUARANTINE_REASONS_TABLE = "dq.dq_quarantine_reasons"

logger = logging.getLogger(__name__)


def _ensure_objects(conn, staging_table: str = STAGING_TABLE) -> None:
    """Проверяет, что staging и core созданы."""
    for table_name, hint in (
        (staging_table, "Сначала выполните staging-шаг пайплайна."),
        (CORE_TABLE, "Сначала инициализируйте схему core (это делает ETL-пайплайн)."),
        (QUARANTINE_TABLE, "Сначала инициализируйте схему dq (это делает ETL-пайплайн)."),
    ):
        exists = conn.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": table_name},
        ).scalar()
        if exists is None:
            raise RuntimeError(f"Нет таблицы {table_name}. {hint}")


def load_validation_results(engine: Engine | None = None) -> LoadResult:
    """Переносит валидные сделки из stg.price_validation в core.prices, а невалидные - в dq.dq_quarantine_prices."""
    engine = engine or create_db_engine()
    run_id = uuid4()

    core_sql = LOAD_CORE_SQL.read_text(encoding="utf-8")
    quarantine_sql = LOAD_QUARANTINE_SQL.read_text(encoding="utf-8")

    logger.info("Загрузка staging в core и карантин: run_id=%s", run_id)
    started_at = time.perf_counter()

    with engine.begin() as conn:
        _ensure_objects(conn)

        reasons = dict(
            conn.execute(text(f"SELECT id, description FROM {QUARANTINE_REASONS_TABLE}")).all()
        )

        reason_stats = conn.execute(
            text(
                f"""
                SELECT r.reason_id, count(*) AS cnt
                FROM {STAGING_TABLE} s
                CROSS JOIN LATERAL unnest(s.dq_reason_ids) AS r(reason_id)
                GROUP BY r.reason_id
                ORDER BY r.reason_id
                """
            )
        ).all()

        if reason_stats:
            logger.info(
                "Карантин по причинам: %s",
                ", ".join(f"\n - {reasons[reason_id]}: {cnt}" for reason_id, cnt in reason_stats),
            )
        else:
            logger.info("Карантин по причинам: нет отбракованных строк")

        core_deleted = conn.execute(
            text(f"DELETE FROM {CORE_TABLE} WHERE price_id IN (SELECT id FROM {STAGING_TABLE})")
        ).rowcount

        core_inserted = conn.execute(
            text(core_sql),
            {"etl_run_id": run_id},
        ).rowcount

        quarantine_deleted = conn.execute(
            text(
                f"DELETE FROM {QUARANTINE_TABLE} WHERE price_id IN (SELECT id FROM {STAGING_TABLE})"
            )
        ).rowcount

        quarantine_inserted = conn.execute(
            text(quarantine_sql),
            {"etl_run_id": run_id},
        ).rowcount

    logger.info(
        "Загрузка завершена: run_id=%s, удалено из core=%s, удалено из карантина=%s, valid=%s, quarantine=%s, %.2f c",
        run_id,
        core_deleted,
        quarantine_deleted,
        core_inserted,
        quarantine_inserted,
        time.perf_counter() - started_at,
    )

    return LoadResult(
        run_id=run_id,
        valid_rows=core_inserted,
        quarantined_rows=quarantine_inserted,
        core_deleted=core_deleted,
        quarantine_deleted=quarantine_deleted,
    )
