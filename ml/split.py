"""Загрузка ML-признаков и хронологическое разбиение train/test."""

import logging
from dataclasses import dataclass

import pandas as pd
import pendulum
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.config import get_as_of_date
from etl.db import create_db_engine
from etl.models import to_pendulum_date

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeSplit:
    """Результат хронологического разбиения."""

    train: pd.DataFrame
    test: pd.DataFrame
    train_start: pendulum.Date
    test_start: pendulum.Date
    test_end: pendulum.Date


def load_price_features(engine: Engine | None = None) -> pd.DataFrame:
    """Читает ml.price_features в DataFrame."""
    engine = engine or create_db_engine()
    query = text("SELECT * FROM ml.price_features ORDER BY loading_date, price_id")

    with engine.connect() as conn:
        data = pd.read_sql(query, conn)

    logger.info("Загружено признаков: %s, колонок: %s", len(data), len(data.columns))
    return data


def split_train_test(
    data: pd.DataFrame,
    as_of: pendulum.Date | pendulum.DateTime | str | None = None,
) -> TimeSplit:
    """Делит данные по loading_date строго по времени.

    train: [as_of - 3 месяца, as_of - 3 недели)
    test:  [as_of - 3 недели, as_of]
    """
    as_of_date = to_pendulum_date(as_of) if as_of is not None else get_as_of_date()
    train_start = as_of_date.subtract(months=3)
    test_start = as_of_date.subtract(weeks=3)

    prepared = data.copy()
    prepared["loading_date"] = pd.to_datetime(prepared["loading_date"])

    train_start_ts = pd.Timestamp(train_start.year, train_start.month, train_start.day)
    test_start_ts = pd.Timestamp(test_start.year, test_start.month, test_start.day)
    test_end_ts = pd.Timestamp(as_of_date.year, as_of_date.month, as_of_date.day)

    train = prepared[
        (prepared["loading_date"] >= train_start_ts)
        & (prepared["loading_date"] < test_start_ts)
    ].copy()
    test = prepared[
        (prepared["loading_date"] >= test_start_ts)
        & (prepared["loading_date"] <= test_end_ts)
    ].copy()

    if train.empty or test.empty:
        raise ValueError("Пустой train или test: проверь окно и данные")

    if train["loading_date"].max() >= test_start_ts:
        raise ValueError("Утечка: в train попали даты >= test_start")
    if test["loading_date"].min() < test_start_ts:
        raise ValueError("В test попали даты < test_start")
    if test["loading_date"].max() > test_end_ts:
        raise ValueError("В test попали даты > as_of")

    outside = len(prepared) - len(train) - len(test)
    if outside:
        logger.warning("Вне train/test осталось %s строк", outside)

    logger.info(
        "Time split: train=%s [%s, %s), test=%s [%s, %s]",
        len(train),
        train_start,
        test_start,
        len(test),
        test_start,
        as_of_date,
    )

    return TimeSplit(
        train=train,
        test=test,
        train_start=train_start,
        test_start=test_start,
        test_end=as_of_date,
    )
