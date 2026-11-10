"""Стейджинг результата валидации сделок."""

import logging
import time
from pathlib import Path

import pendulum
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine
from etl.models import Window

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_VALIDATION_SQL = PROJECT_ROOT.joinpath("sql/transforms/price_validation.sql")

STAGING_SCHEMA = "stg"
STAGING_TABLE = f"{STAGING_SCHEMA}.price_validation"

logger = logging.getLogger(__name__)


def extract_and_stage_window(
    start_date: pendulum.Date | pendulum.DateTime | str,
    end_date: pendulum.Date | pendulum.DateTime | str,
    engine: Engine | None = None,
) -> None:
    """Сохраняет результат DQ-валидации в stg.price_validation."""
    window = Window(
        start_date=start_date,  # type: ignore
        end_date=end_date,  # type: ignore
    )

    query = PRICE_VALIDATION_SQL.read_text(encoding="utf-8")
    engine = engine or create_db_engine()

    logger.info("Стейджинг DQ-валидации: окно [%s, %s)", window.start_date, window.end_date)
    started_at = time.perf_counter()

    with engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {STAGING_SCHEMA}")
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
        conn.execute(
            text(f"CREATE UNLOGGED TABLE {STAGING_TABLE} AS {query}"),
            {"start_date": window.start_date, "end_date": window.end_date},
        )
        conn.exec_driver_sql(
            f"CREATE UNIQUE INDEX {STAGING_TABLE.replace('.', '_')}_id_idx ON {STAGING_TABLE} (id)"
        )
        conn.exec_driver_sql(f"ANALYZE {STAGING_TABLE}")
        stats = (
            conn.execute(
                text(
                    f"""
                    SELECT
                        count(*) AS total,
                        count(*) FILTER (WHERE cardinality(dq_reason_ids) = 0) AS valid,
                        count(*) FILTER (WHERE cardinality(dq_reason_ids) > 0) AS invalid
                    FROM {STAGING_TABLE}
                    """
                )
            )
            .mappings()
            .one()
        )

    logger.info(
        "Staging готов: %s, всего=%s, valid=%s, invalid=%s, %.2f c",
        STAGING_TABLE,
        stats["total"],
        stats["valid"],
        stats["invalid"],
        time.perf_counter() - started_at,
    )
