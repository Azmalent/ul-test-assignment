"""Сборка витрины mart.mart_route_card."""

import logging
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine, execute_sql_script

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MART_BUILD_SQL = PROJECT_ROOT.joinpath("sql/marts/build_mart_route_card.sql")

logger = logging.getLogger(__name__)


def refresh_mart_route_card(engine: Engine | None = None) -> int:
    """Пересобирает mart.mart_route_card и возвращает число строк."""
    engine = engine or create_db_engine()

    logger.info("Сборка витрины mart.mart_route_card...")
    started_at = time.perf_counter()

    execute_sql_script(engine, MART_BUILD_SQL)

    with engine.connect() as conn:
        row_count: int = conn.execute(text("SELECT count(*) FROM mart.mart_route_card")).scalar()  # type: ignore

    logger.info(
        "Витрина mart.mart_route_card собрана: строк=%s, %.2f c",
        row_count,
        time.perf_counter() - started_at,
    )

    return row_count
