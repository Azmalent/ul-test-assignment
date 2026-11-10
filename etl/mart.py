"""Сборка витрины mart.mart_route_card."""

import logging
import time
from pathlib import Path

import pendulum
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.config import get_as_of_date
from etl.db import create_db_engine
from etl.models import to_pendulum_date

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MART_BUILD_SQL = PROJECT_ROOT.joinpath("sql/marts/build_mart_route_card.sql")

logger = logging.getLogger(__name__)


def refresh_mart_route_card(
    engine: Engine | None = None,
    *,
    as_of: pendulum.Date | pendulum.DateTime | str | None = None,
) -> int:
    """Пересобирает mart.mart_route_card и возвращает число строк."""
    engine = engine or create_db_engine()
    as_of_date = to_pendulum_date(as_of) if as_of is not None else get_as_of_date()
    query = MART_BUILD_SQL.read_text(encoding="utf-8")

    logger.info("Сборка витрины mart.mart_route_card, as_of=%s...", as_of_date)
    started_at = time.perf_counter()

    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE mart.mart_route_card")
        conn.execute(text(query), {"as_of": as_of_date})

    with engine.connect() as conn:
        row_count: int = conn.execute(text("SELECT count(*) FROM mart.mart_route_card")).scalar()  # type: ignore

    logger.info(
        "Витрина mart.mart_route_card собрана: строк=%s, %.2f c",
        row_count,
        time.perf_counter() - started_at,
    )

    return row_count
