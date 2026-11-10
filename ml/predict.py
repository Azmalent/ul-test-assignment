"""Batch inference и запись прогнозов в БД."""

import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pendulum
from catboost import CatBoostRegressor
from psycopg2.extras import execute_values
from sqlalchemy.engine import Engine

from etl.config import get_as_of_date
from etl.db import create_db_engine
from etl.models import to_pendulum_date
from ml.dataset import prepare_xy
from ml.features import load_price_features_window
from ml.split import TimeSplit
from ml.train import ARTIFACTS_DIR, MODEL_NAME

logger = logging.getLogger(__name__)

PREDICTION_COLUMNS = (
    "price_id",
    "loading_date",
    "loading_city_gcid",
    "unloading_city_gcid",
    "body_group",
    "actual_price_rub",
    "predicted_price_rub",
    "abs_error_rub",
    "ape_pct",
    "model_name",
)


def load_model(path: Path | str) -> CatBoostRegressor:
    """Загружает CatBoost-модель из файла."""
    model = CatBoostRegressor()
    model.load_model(str(path))
    return model


def build_prediction_frame(
    model: CatBoostRegressor,
    data: pd.DataFrame,
    *,
    model_name: str,
    actual_available: bool,
) -> pd.DataFrame:
    """Считает прогнозы и ошибки для набора строк."""
    features, _ = prepare_xy(data)
    predicted = np.asarray(model.predict(features), dtype=float)

    result = pd.DataFrame(
        {
            "price_id": data["price_id"].to_numpy(),
            "loading_date": pd.to_datetime(data["loading_date"]).dt.date,
            "loading_city_gcid": data["loading_city_gcid"].to_numpy(),
            "unloading_city_gcid": data["unloading_city_gcid"].to_numpy(),
            "body_group": data["body_group"].to_numpy(),
            "predicted_price_rub": predicted,
            "model_name": model_name,
        }
    )

    if actual_available:
        actual = data["target"].astype(float).to_numpy()
        result["actual_price_rub"] = actual
        result["abs_error_rub"] = np.abs(actual - predicted)
        result["ape_pct"] = np.where(
            actual != 0,
            np.abs(actual - predicted) / actual * 100,
            np.nan,
        )
    else:
        result["actual_price_rub"] = None
        result["abs_error_rub"] = None
        result["ape_pct"] = None

    return result


def _clean(value):
    """Превращает NaN/NA в None для корректного NULL в PostgreSQL."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def save_predictions(
    engine: Engine,
    predictions: pd.DataFrame,
    model_name: str,
) -> int:
    """Идемпотентно пишет прогнозы в mart.ml_price_predictions."""
    records = predictions.to_dict("records")
    rows = [
        tuple(_clean(record[column]) for column in PREDICTION_COLUMNS)
        for record in records
    ]
    insert_sql = (
        f"INSERT INTO mart.ml_price_predictions "
        f"({', '.join(PREDICTION_COLUMNS)}) VALUES %s"
    )

    with engine.begin() as conn:
        raw = conn.connection
        with raw.cursor() as cursor:
            cursor.execute(
                "DELETE FROM mart.ml_price_predictions WHERE model_name = %s",
                (model_name,),
            )
            if rows:
                execute_values(cursor, insert_sql, rows, page_size=10000)

    logger.info(
        "Записано прогнозов: %s, model_name=%s",
        len(rows),
        model_name,
    )
    return len(rows)


def run_batch_inference(
    split: TimeSplit,
    as_of: pendulum.Date | pendulum.DateTime | str | None = None,
    engine: Engine | None = None,
    model_path: Path | str | None = None,
) -> int:
    """Скорит test и будущие заявки, затем пишет результат в БД."""
    as_of_date = to_pendulum_date(as_of) if as_of is not None else get_as_of_date()
    engine = engine or create_db_engine()
    resolved_model_path = (
        Path(model_path)
        if model_path is not None
        else ARTIFACTS_DIR.joinpath(f"{MODEL_NAME}.cbm")
    )
    model = load_model(resolved_model_path)

    test_predictions = build_prediction_frame(
        model,
        split.test,
        model_name=MODEL_NAME,
        actual_available=True,
    )

    future_features = load_price_features_window(
        as_of_date.add(days=1),
        as_of_date.add(years=1),
        engine,
        require_fact=False,
    )

    frames = [test_predictions]
    if not future_features.empty:
        frames.append(
            build_prediction_frame(
                model,
                future_features,
                model_name=MODEL_NAME,
                actual_available=False,
            )
        )

    predictions = pd.concat(frames, ignore_index=True)
    return save_predictions(engine, predictions, MODEL_NAME)
