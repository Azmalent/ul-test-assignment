"""Материализация ML-признаков из core.prices."""

import logging
import time
from pathlib import Path

import pandas as pd
import pendulum
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.db import create_db_engine
from etl.models import Window

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_SQL = PROJECT_ROOT.joinpath("sql/ml/features.sql")

FEATURES_TABLE = "ml.price_features"

FEATURE_COLUMNS = (
    "price_id",
    "loading_date",
    "loading_city_gcid",
    "unloading_city_gcid",
    "origin_city",
    "origin_region",
    "origin_lat",
    "origin_lon",
    "destination_city",
    "destination_region",
    "destination_lat",
    "destination_lon",
    "distance",
    "total_weight",
    "total_volume",
    "body_type",
    "body_group",
    "weight_category",
    "volume_category",
    "loading_year",
    "loading_month",
    "loading_dow",
    "loading_doy",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "doy_sin",
    "doy_cos",
    "target",
)

logger = logging.getLogger(__name__)


def load_price_features_window(
    start_date: pendulum.Date | pendulum.DateTime | str,
    end_date: pendulum.Date | pendulum.DateTime | str,
    engine: Engine | None = None,
    *,
    require_fact: bool = False,
) -> pd.DataFrame:
    """Читает признаки за окно без материализации."""
    window = Window(start_date=start_date, end_date=end_date)
    engine = engine or create_db_engine()
    query = FEATURES_SQL.read_text(encoding="utf-8")

    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            {
                "start_date": window.start_date,
                "end_date": window.end_date,
                "require_fact": require_fact,
            },
        ).mappings().all()

    data = pd.DataFrame([dict(row) for row in rows])
    logger.info(
        "Загружено признаков за окно [%s, %s): %s",
        window.start_date,
        window.end_date,
        len(data),
    )
    return data


def refresh_price_features(
    start_date: pendulum.Date | pendulum.DateTime | str,
    end_date: pendulum.Date | pendulum.DateTime | str,
    engine: Engine | None = None,
    *,
    require_fact: bool = True,
) -> int:
    """Пересобирает ml.price_features за окно [start_date, end_date)."""
    window = Window(start_date=start_date, end_date=end_date)  # type: ignore
    engine = engine or create_db_engine()
    query = FEATURES_SQL.read_text(encoding="utf-8")
    insert_sql = f"INSERT INTO {FEATURES_TABLE} ({', '.join(FEATURE_COLUMNS)}) {query}"

    logger.info(
        "Материализация %s: окно [%s, %s), require_fact=%s",
        FEATURES_TABLE,
        window.start_date,
        window.end_date,
        require_fact,
    )
    started_at = time.perf_counter()

    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE TABLE {FEATURES_TABLE}")
        conn.execute(
            text(insert_sql),
            {
                "start_date": window.start_date,
                "end_date": window.end_date,
                "require_fact": require_fact,
            },
        )

    with engine.connect() as conn:
        row_count: int = conn.execute(text(f"SELECT count(*) FROM {FEATURES_TABLE}")).scalar()  # type: ignore

    logger.info(
        "%s собрана: строк=%s, %.2f c",
        FEATURES_TABLE,
        row_count,
        time.perf_counter() - started_at,
    )
    return row_count
