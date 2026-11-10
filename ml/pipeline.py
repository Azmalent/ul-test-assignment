"""Полный ML-пайплайн: признаки -> обучение -> batch inference."""

import logging
import time

import pendulum
from sqlalchemy.engine import Engine

from etl.config import get_as_of_date
from etl.db import create_db_engine
from etl.models import to_pendulum_date
from etl.schemas import init_mart_schema, init_ml_schema
from ml.features import refresh_price_features
from ml.models import MLRunResult
from ml.predict import run_batch_inference
from ml.split import load_price_features, split_train_test
from ml.train import train_and_evaluate

logger = logging.getLogger(__name__)


def run_ml_pipeline(
    as_of: pendulum.Date | pendulum.DateTime | str | None = None,
    engine: Engine | None = None,
) -> MLRunResult:
    """Материализует признаки, обучает модель и пишет прогнозы."""
    as_of_date = to_pendulum_date(as_of) if as_of is not None else get_as_of_date()
    engine = engine or create_db_engine()
    started_at = time.perf_counter()

    logger.info("Старт ML-пайплайна: as_of=%s", as_of_date)

    init_ml_schema(engine)
    init_mart_schema(engine)

    train_start = as_of_date.subtract(months=3)
    features_end = as_of_date.add(days=1)
    feature_rows = refresh_price_features(
        train_start,
        features_end,
        engine,
        require_fact=True,
    )

    data = load_price_features(engine)
    split = split_train_test(data, as_of=as_of_date)
    train_result = train_and_evaluate(split)
    prediction_rows = run_batch_inference(
        split,
        as_of=as_of_date,
        engine=engine,
    )

    logger.info(
        "ML-пайплайн завершён: features=%s, train=%s, test=%s, "
        "test_metrics=%s, predictions=%s, %.2f c",
        feature_rows,
        len(split.train),
        len(split.test),
        train_result.metrics.model_dump(),
        prediction_rows,
        time.perf_counter() - started_at,
    )

    return MLRunResult(
        as_of=as_of_date,
        train=train_result,
        prediction_rows=prediction_rows,
    )
